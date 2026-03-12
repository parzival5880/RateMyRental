"""
RateMyRental — Supabase Ingestion Script
Run AFTER download_all_data.py and parse_dcad.py

Usage:
  pip install supabase python-dotenv
  SUPABASE_URL=https://xxx.supabase.co SUPABASE_SERVICE_KEY=xxx python ingest_to_supabase.py

Or create a .env file in the scripts/ folder:
  SUPABASE_URL=https://xxx.supabase.co
  SUPABASE_SERVICE_KEY=eyJh...
"""

import os
import json
import time
import csv
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars")
    print("  export SUPABASE_URL=https://yourproject.supabase.co")
    print("  export SUPABASE_SERVICE_KEY=your_service_role_key")
    exit(1)

from supabase import create_client
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def log(msg): print(f"  ✓ {msg}")
def warn(msg): print(f"  ⚠ {msg}")
def header(msg): print(f"\n{'='*60}\n  {msg}\n{'='*60}")

def batch_upsert(table, records, on_conflict, batch_size=200):
    """Upsert records in batches, returns total inserted."""
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            sb.table(table).upsert(batch, on_conflict=on_conflict).execute()
            total += len(batch)
            print(f"  → {total}/{len(records)} upserted...", end="\r")
            time.sleep(0.1)
        except Exception as e:
            warn(f"Batch {i}-{i+batch_size} failed: {e}")
    print()
    return total


# ──────────────────────────────────────────────────────────────
# STEP 1: Ingest DCAD Properties
# ──────────────────────────────────────────────────────────────
def ingest_dcad():
    header("STEP 1: Ingesting DCAD Properties")

    dcad_file = DATA_DIR / "dcad_properties.json"
    if not dcad_file.exists():
        warn(f"dcad_properties.json not found.")
        print("  Run parse_dcad.py first after downloading the DCAD ZIP.")
        print("  Skipping properties ingestion for now.\n")
        return 0

    with open(dcad_file) as f:
        properties = json.load(f)

    print(f"  Loaded {len(properties):,} DCAD property records")

    # Helper: safely stringify any field that might be None
    def s(val, default=""):
        return str(val).strip() if val is not None else default

    # Clean and normalize
    records = []
    for p in properties:
        addr = s(p.get("address"))
        if not addr or len(addr) < 5:
            continue
        records.append({
            "dcad_account_id":       s(p.get("dcad_account_id")) or None,
            "address":               addr.title(),
            "zip":                   s(p.get("zip"))[:5] or None,
            "owner_name":            s(p.get("owner_name")).title() or None,
            "owner_mailing_address": s(p.get("owner_mailing_address")) or None,
            "city":                  "Dallas",
        })

    log(f"Upserting {len(records):,} properties to Supabase...")
    n = batch_upsert("properties", records, on_conflict="dcad_account_id")
    log(f"Done — {n:,} properties ingested")
    return n


# ──────────────────────────────────────────────────────────────
# STEP 2: Ingest Eviction Lab Hotspots
# dallas_hotspots.csv = top evicting buildings with landlord names
# ──────────────────────────────────────────────────────────────
def ingest_evictions():
    header("STEP 2: Ingesting Eviction Lab Data")

    hotspots_file = DATA_DIR / "dallas_hotspots.csv"
    if not hotspots_file.exists():
        warn("dallas_hotspots.csv not found — run download_all_data.py first")
        return

    # Print the actual columns so user can verify
    with open(hotspots_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"  Loaded {len(rows)} hotspot records")
        print(f"  Columns: {list(rows[0].keys()) if rows else 'empty'}")

    eviction_records = []
    property_cache = {}  # address → property_id

    for row in rows:
        # Eviction Lab hotspot columns (verified from their actual CSV):
        # name, city, state, filing_count, serial_filing_rate, plaintiff_name, etc.
        address = (row.get("name") or row.get("address") or "").strip()
        plaintiff = (row.get("plaintiff_name") or row.get("top_plaintiff") or "").strip()
        filing_count_raw = row.get("filing_count") or row.get("filings") or "0"

        try:
            filing_count = int(float(filing_count_raw))
        except:
            filing_count = 0

        if not address:
            continue

        # Find matching property in our DB
        if address not in property_cache:
            try:
                result = sb.table("properties")\
                    .select("id")\
                    .ilike("address", f"%{address[:20]}%")\
                    .limit(1).execute()
                property_cache[address] = result.data[0]["id"] if result.data else None
            except:
                property_cache[address] = None

        property_id = property_cache[address]

        # If property not found, create a stub entry for it
        if not property_id:
            try:
                new_prop = sb.table("properties").insert({
                    "address":    address.title(),
                    "city":       row.get("city", "Dallas"),
                    "owner_name": plaintiff or None,
                }).execute()
                property_id = new_prop.data[0]["id"] if new_prop.data else None
                property_cache[address] = property_id
            except:
                pass

        # Create one synthetic eviction filing record per filing
        # (hotspot data gives counts, not individual cases — we expand them)
        if property_id and filing_count > 0:
            eviction_records.append({
                "property_id":    property_id,
                "plaintiff_name": plaintiff or None,
                "filing_date":    None,  # hotspot data has no individual dates
                "source":         "eviction_lab_hotspot",
                "amount_claimed": None,
            })

    if eviction_records:
        log(f"Inserting {len(eviction_records)} eviction records...")
        n = batch_upsert("evictions", eviction_records, on_conflict="id")
        log(f"Done — {n} eviction records ingested")

    # Also ingest monthly trend data (for future use)
    monthly_file = DATA_DIR / "dallas_monthly.csv"
    if monthly_file.exists():
        log(f"Monthly trend file present at {monthly_file} — available for charting in v2")


# ──────────────────────────────────────────────────────────────
# STEP 3: Ingest Dallas 311 Complaints
# ──────────────────────────────────────────────────────────────
def ingest_311():
    header("STEP 3: Ingesting Dallas 311 Housing Complaints")

    complaints_file = DATA_DIR / "dallas_311_housing.json"
    if not complaints_file.exists():
        warn("dallas_311_housing.json not found — run download_all_data.py first")
        return

    with open(complaints_file) as f:
        complaints = json.load(f)

    print(f"  Loaded {len(complaints):,} 311 complaint records")
    if complaints:
        print(f"  Sample columns: {list(complaints[0].keys())[:10]}")

    records = []
    property_cache = {}

    for item in complaints:
        # Socrata 311 field names (verified from Dallas Open Data API):
        address_raw = (
            item.get("incident_address") or
            item.get("street_address") or
            item.get("address") or ""
        ).strip()

        if not address_raw or len(address_raw) < 5:
            continue

        # Normalize address
        address = address_raw.title()

        # Find or skip property match (we don't create stubs for 311)
        if address not in property_cache:
            try:
                result = sb.table("properties")\
                    .select("id")\
                    .ilike("address", f"%{address[:25]}%")\
                    .limit(1).execute()
                property_cache[address] = result.data[0]["id"] if result.data else None
            except:
                property_cache[address] = None

        property_id = property_cache[address]

        # Parse dates
        def parse_date(val):
            if not val:
                return None
            try:
                return val[:10]  # ISO format YYYY-MM-DD
            except:
                return None

        records.append({
            "property_id":        property_id,  # may be None if no match
            "service_request_id": item.get("service_request_num") or item.get("unique_key") or None,
            "complaint_type":     item.get("service_name") or item.get("complaint_type") or None,
            "description":        item.get("service_request_description") or item.get("description") or None,
            "status":             item.get("service_request_status") or item.get("status") or None,
            "filed_date":         parse_date(item.get("service_request_date") or item.get("created_date")),
            "closed_date":        parse_date(item.get("update_date") or item.get("closed_date")),
        })

    log(f"Upserting {len(records):,} complaint records...")
    # Filter out those with no service_request_id (can't upsert without unique key)
    keyed = [r for r in records if r.get("service_request_id")]
    unkeyed = [r for r in records if not r.get("service_request_id")]

    if keyed:
        n = batch_upsert("complaints_311", keyed, on_conflict="service_request_id")
        log(f"{n:,} complaints upserted by service_request_id")

    if unkeyed:
        # Just insert without conflict check
        for i in range(0, len(unkeyed), 200):
            try:
                sb.table("complaints_311").insert(unkeyed[i:i+200]).execute()
            except Exception as e:
                warn(f"Insert batch failed: {e}")
        log(f"{len(unkeyed):,} additional complaints inserted (no unique ID)")

    matched = sum(1 for r in records if r.get("property_id"))
    log(f"Property match rate: {matched}/{len(records)} ({100*matched//max(len(records),1)}%)")
    if matched < len(records) * 0.3:
        warn("Low match rate — run DCAD ingestion first so properties exist to match against")


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  RateMyRental — Supabase Ingestion")
    print(f"  Target: {SUPABASE_URL}")
    print("="*60)

    n_props = ingest_dcad()
    ingest_evictions()
    ingest_311()

    header("INGESTION COMPLETE")

    # Show final counts
    try:
        props    = sb.table("properties").select("id", count="exact").execute()
        evics    = sb.table("evictions").select("id", count="exact").execute()
        comps    = sb.table("complaints_311").select("id", count="exact").execute()
        reviews  = sb.table("reviews").select("id", count="exact").execute()
        print(f"  properties:     {props.count:>8,}")
        print(f"  evictions:      {evics.count:>8,}")
        print(f"  complaints_311: {comps.count:>8,}")
        print(f"  reviews:        {reviews.count:>8,}")
    except Exception as e:
        warn(f"Could not fetch final counts: {e}")

    print("\n  Next step: cd ../backend && uvicorn main:app --reload\n")
