"""
RateMyRental — AI Service
Handles all AI features:
  1. Property risk summary
  2. Lease red flag scanner
  3. Tenant rights chat

Supports two backends (auto-detected via env vars):
  - LOCAL:  Ollama  (OLLAMA_BASE_URL=http://localhost:11434)
  - CLOUD:  OpenRouter / any OpenAI-compatible API
            (AI_PROVIDER=openrouter, OPENROUTER_API_KEY=sk-or-...)
"""

from __future__ import annotations
import os
import re
import json
import requests
from typing import Generator, Union

# ── Backend config ──────────────────────────────────────────────
AI_PROVIDER      = os.environ.get("AI_PROVIDER", "ollama").lower()   # "ollama" or "openrouter"
OLLAMA_BASE_URL  = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL     = os.environ.get("OLLAMA_MODEL", "deepseek-r1:14b")

# OpenRouter / OpenAI-compatible cloud backend
OPENROUTER_KEY   = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-r1-0528:free")

# Dallas tenant law context injected into every chat response
DALLAS_TENANT_LAW_CONTEXT = """
Key Dallas / Texas tenant rights:
- Security deposits: Landlord must return within 30 days of move-out with itemized deductions. Normal wear and tear cannot be deducted.
- Repairs: Tenant must give written notice. Landlord has reasonable time (usually 7 days for non-emergency, 3 days for emergency) to repair.
- Eviction: Landlord must give written notice (3-day notice for non-payment) before filing in Justice of the Peace court. Self-help eviction (changing locks, removing belongings) is illegal.
- Retaliation: Landlord cannot evict or raise rent within 6 months of tenant reporting code violations.
- Habitability: Unit must have working heat, plumbing, and be free of rodents/pests.
- Dallas specifics: Dallas has a Tenant Notification Ordinance requiring 60-day notice for rent increases over 10%.
"""


# ── Provider dispatch ────────────────────────────────────────────

def _call_ai(prompt: str, system: str = "", stream: bool = False) -> Union[str, Generator]:
    """Route to Ollama or OpenRouter based on AI_PROVIDER env var."""
    if AI_PROVIDER == "openrouter" and OPENROUTER_KEY:
        return _call_openrouter(prompt, system=system, stream=stream)
    return _call_ollama(prompt, system=system, stream=stream)


def is_ai_available() -> bool:
    """Check if the configured AI backend is reachable."""
    if AI_PROVIDER == "openrouter" and OPENROUTER_KEY:
        return True  # API key present = assume available
    return _is_ollama_available()


# Keep old name for backwards compat with main.py
def is_ollama_available() -> bool:
    return is_ai_available()


# ── Ollama (local) ───────────────────────────────────────────────

def _call_ollama(prompt: str, system: str = "", stream: bool = False) -> Union[str, Generator]:
    """Call Ollama API. Returns full text or a generator for streaming."""
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": 0.3,
            "num_predict": 1024,
        }
    }
    if system:
        payload["system"] = system

    if stream:
        def _stream():
            with requests.post(
                f"{OLLAMA_BASE_URL}/api/generate", json=payload, stream=True, timeout=120
            ) as r:
                for line in r.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        yield chunk.get("response", "")
                        if chunk.get("done"):
                            break
        return _stream()

    r = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=120)
    r.raise_for_status()
    return r.json().get("response", "")


def _is_ollama_available() -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        return any(OLLAMA_MODEL.split(":")[0] in m for m in models)
    except:
        return False


# ── OpenRouter (production cloud) ───────────────────────────────

def _call_openrouter(prompt: str, system: str = "", stream: bool = False) -> Union[str, Generator]:
    """Call OpenRouter (OpenAI-compatible) API."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://ratemyrental.app",
        "X-Title":       "RateMyRental",
    }
    payload = {
        "model":       OPENROUTER_MODEL,
        "messages":    messages,
        "temperature": 0.3,
        "max_tokens":  1024,
        "stream":      stream,
    }

    if stream:
        def _stream():
            with requests.post(
                OPENROUTER_URL, json=payload, headers=headers, stream=True, timeout=120
            ) as r:
                for line in r.iter_lines():
                    if not line:
                        continue
                    text = line.decode("utf-8")
                    if text.startswith("data: "):
                        text = text[6:]
                    if text == "[DONE]":
                        break
                    try:
                        chunk = json.loads(text)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except:
                        continue
        return _stream()

    r = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# ── JSON helpers ─────────────────────────────────────────────────

def _extract_json(response: str) -> dict | None:
    """Strip <think> tags and extract the first JSON object from a response."""
    clean = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
    match = re.search(r'\{.*\}', clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return None


# ──────────────────────────────────────────────────────────────
# FEATURE 1: AI Property Risk Summary
# ──────────────────────────────────────────────────────────────

def generate_property_report(property_data: dict) -> dict:
    """
    Generate a plain-English AI risk summary for a property.
    Returns: { summary, risk_level, risk_factors }
    """
    prop     = property_data.get("property", {})
    evics    = property_data.get("evictions", [])
    comps    = property_data.get("complaints", [])
    reviews  = property_data.get("reviews", [])
    red_flag = property_data.get("red_flag", {})

    avg_rating = None
    if reviews:
        avg_rating = round(
            sum(
                (r.get("maintenance_score", 3) + r.get("lease_fairness", 3) + r.get("communication_score", 3)) / 3
                for r in reviews
            ) / len(reviews), 1
        )

    comp_types: dict = {}
    for c in comps:
        t = c.get("complaint_type", "Unknown")
        comp_types[t] = comp_types.get(t, 0) + 1
    comp_summary = ", ".join(
        f"{v}x {k}" for k, v in sorted(comp_types.items(), key=lambda x: -x[1])[:3]
    )

    prompt = f"""You are a tenant advocate analyzing a Dallas rental property. Be direct, factual, and helpful to renters.

PROPERTY DATA:
- Address: {prop.get('address', 'Unknown')}, Dallas TX {prop.get('zip', '')}
- Owner: {prop.get('owner_name', 'Unknown')}
- Owner mailing address: {prop.get('owner_mailing_address', 'Unknown')} (note if different state = out-of-state landlord)
- Property type: {prop.get('property_type', 'Unknown')}, built {prop.get('year_built', 'Unknown')}
- Eviction filings: {len(evics)} total
- 311 complaints: {len(comps)} total ({comp_summary or 'none on record'})
- Tenant reviews: {len(reviews)} ({f'avg rating {avg_rating}/5' if avg_rating else 'no reviews yet'})
- Risk score: {red_flag.get('score', 0)}/100 ({red_flag.get('color', 'unknown')} flag)

Write a 3-sentence plain-English summary a renter can read in 5 seconds. Then list 3-5 specific risk factors as a JSON array.

Respond in this exact JSON format (no extra text):
{{
  "summary": "2-3 sentence plain English summary",
  "risk_level": "low|medium|high",
  "risk_factors": [
    "Risk factor 1",
    "Risk factor 2",
    "Risk factor 3"
  ]
}}"""

    response = _call_ai(prompt)
    result = _extract_json(response)
    if result:
        return result

    return {
        "summary": response[:500] if response else "AI analysis unavailable.",
        "risk_level": red_flag.get("color", "medium"),
        "risk_factors": ["AI summary generation failed — see raw data above"],
    }


# ──────────────────────────────────────────────────────────────
# FEATURE 2: AI Lease Scanner
# ──────────────────────────────────────────────────────────────

def scan_lease(lease_text: str) -> dict:
    """
    Analyze lease text for red flags and missing protections.
    Returns structured findings a tenant can act on.
    """
    truncated = lease_text[:8000]
    if len(lease_text) > 8000:
        truncated += "\n[... lease truncated for analysis ...]"

    prompt = f"""You are a tenant advocate lawyer reviewing a Dallas Texas lease. Analyze this lease and find issues that could harm the tenant.

LEASE TEXT:
{truncated}

Analyze and respond in this exact JSON format (no extra text, no <think> tags):
{{
  "red_flags": [
    {{"clause": "exact quote from lease", "issue": "why this harms tenant", "severity": "high|medium|low"}}
  ],
  "missing_protections": [
    "Protection that should be in the lease but isn't"
  ],
  "positive_clauses": [
    "Good tenant-friendly clause found"
  ],
  "overall_verdict": "1-2 sentence plain English verdict",
  "tenant_friendliness_score": 7
}}

Focus on: automatic renewal traps, excessive fees, waived rights, illegal clauses, security deposit terms, repair responsibilities, entry notice requirements, early termination penalties."""

    response = _call_ai(prompt)
    result = _extract_json(response)
    if result:
        return result

    return {
        "red_flags": [],
        "missing_protections": [],
        "positive_clauses": [],
        "overall_verdict": "Analysis failed. Please try again.",
        "tenant_friendliness_score": 5,
        "raw_response": response[:1000],
    }


# ──────────────────────────────────────────────────────────────
# FEATURE 3: Tenant Rights Chat
# ──────────────────────────────────────────────────────────────

def chat_tenant_rights(question: str, stream: bool = True):
    """
    Answer tenant rights questions with Dallas-specific context.
    Streams response for real-time display.
    """
    system = f"""You are a helpful tenant rights advisor specializing in Dallas, Texas rental law.
You give practical, plain-English advice to renters.
Always clarify you are not a lawyer and serious issues should consult a legal aid organization.
Dallas Legal Aid: 214-748-1234
Texas RioGrande Legal Aid: texaslawhelp.org

{DALLAS_TENANT_LAW_CONTEXT}

Be concise (3-5 sentences). End with one actionable next step."""

    if stream:
        return _call_ai(question, system=system, stream=True)
    else:
        return {"response": _call_ai(question, system=system, stream=False)}
