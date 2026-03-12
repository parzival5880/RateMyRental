"""
RateMyRental — FastAPI Backend
All API endpoints for the frontend + AI features.

Run: uvicorn main:app --reload --port 8000
"""

from __future__ import annotations
import os
import hashlib
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from supabase import create_client
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI(title="RateMyRental API", version="1.0.0")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import AI service
from ai_service import generate_property_report, scan_lease, chat_tenant_rights, is_ollama_available


# ──────────────────────────────────────────────────────────────
# HEALTH CHECK
# ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ollama": is_ollama_available(),
        "supabase": SUPABASE_URL,
    }


# ──────────────────────────────────────────────────────────────
# SEARCH — address or landlord name
# ──────────────────────────────────────────────────────────────

@app.get("/api/search")
async def search(q: str):
    if len(q) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")
    try:
        result = sb.rpc("search_properties", {"query": q}).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────
# PROPERTY DETAIL — full data for one property
# ──────────────────────────────────────────────────────────────

@app.get("/api/property/{property_id}")
async def get_property(property_id: str):
    prop = sb.table("properties").select("*").eq("id", property_id).single().execute()
    if not prop.data:
        raise HTTPException(status_code=404, detail="Property not found")

    evictions  = sb.table("evictions").select("*").eq("property_id", property_id).order("filing_date", desc=True).execute()
    complaints = sb.table("complaints_311").select("*").eq("property_id", property_id).order("filed_date", desc=True).execute()
    reviews    = sb.table("reviews").select("*").eq("property_id", property_id).order("submitted_at", desc=True).execute()

    # Red flag score
    ev_count   = len(evictions.data)
    comp_count = len(complaints.data)
    rev_data   = reviews.data
    avg_rating = (
        sum((r.get("maintenance_score", 3) + r.get("lease_fairness", 3) + r.get("communication_score", 3)) / 3
            for r in rev_data) / len(rev_data)
        if rev_data else None
    )
    score = min(100, (ev_count * 10) + (comp_count * 2) + (0 if avg_rating is None else (5 - avg_rating) * 10))
    flag  = "green" if score < 25 else "yellow" if score < 60 else "red"

    # Check for cached AI summary
    ai_cached = sb.table("ai_summaries").select("*").eq("property_id", property_id).execute()
    ai_summary = ai_cached.data[0] if ai_cached.data else None

    return {
        "property":   prop.data,
        "evictions":  evictions.data,
        "complaints": complaints.data,
        "reviews":    rev_data,
        "red_flag":   {"score": round(score), "color": flag},
        "ai_summary": ai_summary,
    }


# ──────────────────────────────────────────────────────────────
# AI FEATURE 1: Property AI Report
# ──────────────────────────────────────────────────────────────

@app.post("/api/property/{property_id}/ai-report")
@limiter.limit("10/minute")
async def get_ai_report(property_id: str, request: Request):
    """Generate and cache an AI risk summary for a property."""

    # Check cache first
    cached = sb.table("ai_summaries").select("*").eq("property_id", property_id).execute()
    if cached.data:
        return {"cached": True, **cached.data[0]}

    if not is_ollama_available():
        raise HTTPException(status_code=503, detail="AI service not available. Make sure Ollama is running.")

    # Fetch all property data
    prop_data = await get_property(property_id)

    # Generate AI report
    report = generate_property_report(prop_data)

    # Cache in Supabase
    try:
        sb.table("ai_summaries").upsert({
            "property_id": property_id,
            "summary":     report.get("summary", ""),
            "risk_level":  report.get("risk_level", "medium"),
            "risk_factors": report.get("risk_factors", []),
            "model_used":  os.environ.get("OLLAMA_MODEL", "deepseek-r1:14b"),
        }, on_conflict="property_id").execute()
    except Exception as e:
        pass  # Cache failure shouldn't break the response

    return {"cached": False, **report}


# ──────────────────────────────────────────────────────────────
# AI FEATURE 2: Lease Scanner
# ──────────────────────────────────────────────────────────────

class LeaseInput(BaseModel):
    lease_text: str

@app.post("/api/lease/scan")
@limiter.limit("5/minute")
async def scan_lease_endpoint(data: LeaseInput, request: Request):
    """Scan a lease for red flags using AI."""
    if len(data.lease_text) < 100:
        raise HTTPException(status_code=400, detail="Lease text too short (minimum 100 characters)")
    if len(data.lease_text) > 50000:
        raise HTTPException(status_code=400, detail="Lease text too long (max 50,000 characters)")

    if not is_ollama_available():
        raise HTTPException(status_code=503, detail="AI service not available. Make sure Ollama is running.")

    result = scan_lease(data.lease_text)

    # Log scan (no PII stored)
    try:
        ip_hash = hashlib.sha256(request.client.host.encode()).hexdigest()
        sb.table("lease_scans").insert({
            "ip_hash": ip_hash,
            "red_flags_count": len(result.get("red_flags", [])),
        }).execute()
    except:
        pass

    return result


# ──────────────────────────────────────────────────────────────
# AI FEATURE 3: Tenant Rights Chat (streaming)
# ──────────────────────────────────────────────────────────────

class ChatInput(BaseModel):
    question: str

@app.post("/api/chat")
@limiter.limit("20/minute")
async def chat_endpoint(data: ChatInput, request: Request):
    """Stream a tenant rights answer from the AI."""
    if len(data.question) < 5:
        raise HTTPException(status_code=400, detail="Question too short")
    if len(data.question) > 1000:
        raise HTTPException(status_code=400, detail="Question too long (max 1000 chars)")

    if not is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="AI service not available. Make sure Ollama is running with: ollama serve"
        )

    def stream_generator():
        for chunk in chat_tenant_rights(data.question, stream=True):
            # SSE format
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


# ──────────────────────────────────────────────────────────────
# REVIEWS — submit a tenant review
# ──────────────────────────────────────────────────────────────

class ReviewIn(BaseModel):
    property_id: str
    landlord_name: str
    maintenance_score: int
    deposit_returned: str
    deposit_days: Optional[int] = None
    lease_fairness: int
    communication_score: int
    would_rent_again: bool
    comments: str | None = None

@app.post("/api/review")
@limiter.limit("3/hour")
async def submit_review(review: ReviewIn, request: Request):
    ip = request.client.host
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()

    # 1 review per property per IP
    existing = sb.table("reviews").select("id")\
        .eq("property_id", review.property_id)\
        .eq("ip_hash", ip_hash).execute()
    if existing.data:
        raise HTTPException(status_code=429, detail="You have already reviewed this property")

    # Validate scores
    for field in ["maintenance_score", "lease_fairness", "communication_score"]:
        val = getattr(review, field)
        if not 1 <= val <= 5:
            raise HTTPException(status_code=400, detail=f"{field} must be between 1 and 5")

    data = review.model_dump()
    data["ip_hash"] = ip_hash

    sb.table("reviews").insert(data).execute()

    # Invalidate AI cache so it gets regenerated with new review data
    try:
        sb.table("ai_summaries").delete().eq("property_id", review.property_id).execute()
    except:
        pass

    return {"ok": True, "message": "Review submitted successfully"}
