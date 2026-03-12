"""
RateMyRental — Master Data Downloader
Run this script ONCE to pull all data you need.

Usage:
  pip install requests tqdm
  python download_all_data.py

All files land in ./data/ folder next to this script.
"""

import os
import json
import time
import requests
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

def log(msg): print(f"  ✓ {msg}")
def warn(msg): print(f"  ⚠ {msg}")
def header(msg): print(f"\n{'='*60}\n  {msg}\n{'='*60}")


# ──────────────────────────────────────────────────────────────
# SOURCE 1: EVICTION LAB (Princeton) — Direct CSV downloads
# No login, no key, no rate limit
# ──────────────────────────────────────────────────────────────
def download_eviction_lab():
    header("SOURCE 1: Eviction Lab — Dallas TX Data")

    files = {
        "dallas_hotspots.csv":      "https://evictionlab.org/uploads/dallas_hotspots_media_report.csv",
        "dallas_monthly.csv":       "https://evictionlab.org/uploads/dallas_barchart.csv",
        "dallas_claims.csv":        "https://evictionlab.org/uploads/dallas_claims_monthly.csv",
        "dallas_map.csv":           "https://evictionlab.org/uploads/dallas_map.csv",
        "dallas_demographics.csv":  "https://evictionlab.org/uploads/dallas_linechart.csv",
    }

    for filename, url in files.items():
        dest = DATA_DIR / filename
        if dest.exists():
            log(f"Already exists, skipping: {filename}")
            continue
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            dest.write_bytes(r.content)
            rows = len(r.text.splitlines()) - 1
            log(f"Downloaded {filename} ({rows} rows, {len(r.content)//1024}KB)")
        except Exception as e:
            warn(f"Failed {filename}: {e}")

    print("""
  KEY FILE → dallas_hotspots.csv
  Contains top evicting buildings + plaintiff (landlord) names.
  Columns to use: address, plaintiff_name, filing_count, city, zip
""")


# ──────────────────────────────────────────────────────────────
# SOURCE 2: DALLAS 311 OPEN DATA — Socrata API
# Dataset ID: gc4d-8a49 (main live dataset, updated March 2026)
# No API key required for up to 1000 rows/request
# ──────────────────────────────────────────────────────────────
def download_311_complaints():
    header("SOURCE 2: Dallas 311 Open Data — Housing Complaints")

    # These are the complaint types relevant to housing/rental issues
    HOUSING_SERVICE_NAMES = [
        "Overgrown Weeds/Grass",
        "Property Maintenance",
        "Junk/Debris",
        "Substandard Structure - Occupied",
        "Substandard Structure - Unoccupied",
        "Code Compliance",
        "Housing Code Compliance",
    ]

    BASE_URL = "https://www.dallasopendata.com/resource/gc4d-8a49.json"
    dest = DATA_DIR / "dallas_311_housing.json"

    all_records = []
    offset = 0
    limit = 1000
    max_records = 50000  # cap for POC — about 50MB

    print(f"  Fetching housing-related 311 complaints (up to {max_records} records)...")
    print(f"  This may take several minutes — Socrata API, 1000 rows at a time\n")

    while offset < max_records:
        # Build SoQL WHERE clause
        where_clause = " OR ".join([f"service_name='{s}'" for s in HOUSING_SERVICE_NAMES])
        params = {
            "$limit":  limit,
            "$offset": offset,
            "$where":  where_clause,
            "$order":  "service_request_date DESC",
        }

        try:
            r = requests.get(BASE_URL, params=params, timeout=30)
            if r.status_code == 200:
                batch = r.json()
                if not batch:
                    print(f"  → No more records at offset {offset}. Done.")
                    break
                all_records.extend(batch)
                print(f"  → Fetched {len(all_records)} records so far...", end="\r")
                offset += limit
                time.sleep(0.3)  # be polite to the API
            else:
                warn(f"API error {r.status_code} at offset {offset}: {r.text[:200]}")
                break
        except Exception as e:
            warn(f"Request failed at offset {offset}: {e}")
            break

    if all_records:
        dest.write_text(json.dumps(all_records, indent=2))
        log(f"\n  Saved {len(all_records)} 311 housing complaints → {dest.name}")
        log(f"  File size: {dest.stat().st_size // 1024}KB")

        # Show sample of what complaint types we got
        types = {}
        for r in all_records:
            t = r.get("service_name", "unknown")
            types[t] = types.get(t, 0) + 1
        print("\n  Complaint type breakdown:")
        for t, count in sorted(types.items(), key=lambda x: -x[1]):
            print(f"    {count:>6,}  {t}")
    else:
        warn("No 311 records retrieved — check API endpoint")
        print("  Manual fallback: visit https://www.dallasopendata.com/d/gc4d-8a49")
        print("  Click Export → CSV → Download")


# ──────────────────────────────────────────────────────────────
# SOURCE 3: DCAD — Property Ownership Data
# The download links on dallascad.org are SESSION-BASED (cookies).
# Python cannot replicate them automatically.
# → You must download manually (takes 2 minutes).
# ──────────────────────────────────────────────────────────────
def instructions_dcad():
    header("SOURCE 3: DCAD Property Data — MANUAL DOWNLOAD REQUIRED")
    print("""
  DCAD uses session-authenticated download links (cookie-based).
  Python cannot automate this. You need to do it once manually:

  STEP 1: Open this URL in your browser:
          https://www.dallascad.org/DataProducts.aspx

  STEP 2: Click this link on the page:
          "2026 Data Files (No Values - Most Current Ownership)"
          (First link under "Current and Prior Appraisal data")

  STEP 3: A large ZIP file will download (~200-400MB).
          It contains multiple CSV files inside.

  STEP 4: Unzip it and move the contents into:
          RateMyRental/scripts/data/dcad/

  STEP 5: Run parse_dcad.py (auto-created below) to process it.

  KEY FILES inside the ZIP:
    - REAL PROPERTY ACCOUNT  → has address + owner name
    - OWNER INFO             → has owner mailing address
    - PROPERTY INFORMATION   → has property type / land use code

  You only need those 3 files. Ignore the rest.
""")

    # Create the parser script for after they download
    dcad_parser = Path(__file__).parent / "parse_dcad.py"
    dcad_parser.write_text('''"""
Run AFTER downloading and unzipping the DCAD data.
Place unzipped files in: scripts/data/dcad/
Then run: python parse_dcad.py
"""
import pandas as pd
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DCAD_DIR = DATA_DIR / "dcad"

# Find the real property file (name varies by year)
import glob
candidates = glob.glob(str(DCAD_DIR / "*.csv")) + glob.glob(str(DCAD_DIR / "*REAL*")) + glob.glob(str(DCAD_DIR / "*real*"))
print(f"Found {len(candidates)} files in dcad/ folder:")
for f in candidates:
    print(f"  {f}")

# Try to auto-detect the right file
real_prop_file = None
for c in candidates:
    try:
        df_test = pd.read_csv(c, nrows=5, dtype=str, encoding="latin1")
        cols = [col.upper() for col in df_test.columns]
        if any("ACCOUNT" in c for c in cols) and any("ADDRESS" in c or "SITUS" in c for c in cols):
            real_prop_file = c
            print(f"\\nDetected real property file: {c}")
            print(f"Columns: {list(df_test.columns)}")
            break
    except:
        pass

if not real_prop_file:
    print("\\nCould not auto-detect file. Please set real_prop_file manually.")
    print("Look for a file with columns like: ACCOUNT_NUM, SITUS_ADDRESS, OWNER_NAME")
else:
    df = pd.read_csv(real_prop_file, dtype=str, encoding="latin1", low_memory=False)
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    print(f"\\nLoaded {len(df):,} property records")
    print(f"Columns: {list(df.columns)[:15]}")

    # Normalize — map whatever column names DCAD uses this year
    col_map = {}
    for col in df.columns:
        if "ACCOUNT" in col: col_map["dcad_account_id"] = col
        elif "SITUS" in col and "ADDR" in col: col_map["address"] = col
        elif "SITUS" in col and "ZIP" in col: col_map["zip"] = col
        elif "OWNER" in col and "NAME" in col: col_map["owner_name"] = col
        elif "OWNER" in col and ("ADDR" in col or "MAIL" in col): col_map["owner_address"] = col

    print(f"\\nColumn mapping detected: {col_map}")

    out = []
    for _, row in df.iterrows():
        rec = {}
        for field, col in col_map.items():
            rec[field] = str(row.get(col, "")).strip()
        # Only include residential/multi-family (skip commercial land)
        out.append(rec)

    output_file = DATA_DIR / "dcad_properties.json"
    with open(output_file, "w") as f:
        json.dump(out, f)
    print(f"\\nSaved {len(out):,} properties → {output_file}")
    print("Now run: python ingest_to_supabase.py")
''')
    log(f"Created parse_dcad.py — run it after unzipping the DCAD ZIP")


# ──────────────────────────────────────────────────────────────
# SOURCE 4: EVICTION LAB — "Get the Data" full dataset
# Larger dataset with individual-level filing data
# Requires a free account to download the big file
# ──────────────────────────────────────────────────────────────
def instructions_eviction_lab_full():
    header("SOURCE 4: Eviction Lab — Full Dataset (Optional for v2)")
    print("""
  The files we downloaded in Source 1 are already enough for POC.

  If you want the full address-level dataset later:
  1. Go to: https://evictionlab.org/get-the-data/
  2. Fill out a short form (name + email + use case)
  3. They email you a download link within minutes
  4. Download the Texas state file (~1GB)
  5. Filter for Dallas County (FIPS code: 48113)

  For the POC, skip this — dallas_hotspots.csv has what you need.
""")


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  RateMyRental — Data Downloader")
    print("  All files → scripts/data/")
    print("="*60)

    download_eviction_lab()
    download_311_complaints()
    instructions_dcad()
    instructions_eviction_lab_full()

    header("SUMMARY")
    print("  Files downloaded automatically:")
    for f in sorted(DATA_DIR.glob("*.csv")) + sorted(DATA_DIR.glob("*.json")):
        size = f.stat().st_size // 1024
        print(f"    {f.name:<35} {size:>6} KB")

    print("""
  Still needed (manual):
    → DCAD ZIP from dallascad.org/DataProducts.aspx  (see instructions above)

  Next step after all data is in place:
    python ingest_to_supabase.py
""")
