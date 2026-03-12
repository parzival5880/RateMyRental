"""
RateMyRental — DCAD Parser (Fixed for 2025 data structure)
Reads from: scripts/data/DCAD2025_CURRENT/
Writes to:  scripts/data/dcad_properties.json

Usage:
  pip install pandas
  python3 parse_dcad.py
"""

import pandas as pd
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# Auto-detect the DCAD folder (handles any year name like DCAD2025_CURRENT)
DCAD_DIR = None
for candidate in sorted(DATA_DIR.iterdir()):
    if candidate.is_dir() and "DCAD" in candidate.name.upper():
        DCAD_DIR = candidate
        break

if not DCAD_DIR:
    print("ERROR: Could not find DCAD folder inside scripts/data/")
    print("Expected a folder named like: DCAD2025_CURRENT")
    print(f"Folders found: {[d.name for d in DATA_DIR.iterdir() if d.is_dir()]}")
    exit(1)

print(f"\n✓ Found DCAD folder: {DCAD_DIR.name}")
print(f"  Files: {[f.name for f in DCAD_DIR.glob('*.CSV')]}\n")


# ──────────────────────────────────────────────────────────────
# STEP 1: Load ACCOUNT_INFO.CSV
# This is the master file — has account#, owner name, and
# the property's situs address split across multiple columns
# ──────────────────────────────────────────────────────────────
print("Loading ACCOUNT_INFO.CSV...")
account_file = DCAD_DIR / "ACCOUNT_INFO.CSV"

if not account_file.exists():
    print(f"ERROR: {account_file} not found")
    exit(1)

df = pd.read_csv(
    account_file,
    dtype=str,
    encoding="latin1",
    low_memory=False,
    quotechar='"',
)
df = df.fillna("")
df.columns = [c.strip().strip('"') for c in df.columns]

print(f"  Loaded {len(df):,} records")
print(f"  Columns: {list(df.columns)}\n")

# Verified 2025 columns from actual file:
# ACCOUNT_NUM, APPRAISAL_YR, DIVISION_CD, BIZ_NAME, OWNER_NAME1, OWNER_NAME2,
# EXCLUDE_OWNER, OWNER_ADDRESS_LINE1..4, OWNER_CITY, OWNER_STATE, OWNER_ZIPCODE,
# OWNER_COUNTRY, STREET_NUM, STREET_HALF_NUM, FULL_STREET_NAME, BLDG_ID, UNIT_ID,
# PROPERTY_CITY, PROPERTY_ZIPCODE, MAPSCO, NBHD_CD, LEGAL1..5, DEED_TXFR_DATE,
# GIS_PARCEL_ID, PHONE_NUM, LMA, IMA


# ──────────────────────────────────────────────────────────────
# STEP 2: Load RES_DETAIL.CSV for property type + unit count
# Join on ACCOUNT_NUM to tag residential multi-family
# ──────────────────────────────────────────────────────────────
print("Loading RES_DETAIL.CSV for property type info...")
res_file = DCAD_DIR / "RES_DETAIL.CSV"

res_df = pd.read_csv(
    res_file,
    dtype=str,
    encoding="latin1",
    low_memory=False,
    quotechar='"',
    usecols=["ACCOUNT_NUM", "BLDG_CLASS_DESC", "NUM_UNITS", "YR_BUILT"],
)
res_df = res_df.fillna("")
res_df.columns = [c.strip().strip('"') for c in res_df.columns]

# Keep only the first row per account (some have multiple buildings)
res_df = res_df.drop_duplicates(subset="ACCOUNT_NUM", keep="first")
res_lookup = res_df.set_index("ACCOUNT_NUM").to_dict("index")

print(f"  Loaded {len(res_df):,} residential property records\n")


# ──────────────────────────────────────────────────────────────
# STEP 3: Build the output — one record per property
# ──────────────────────────────────────────────────────────────
print("Building property records...")

out = []
skipped = 0

for _, row in df.iterrows():
    account_num = row.get("ACCOUNT_NUM", "").strip()

    # Build the situs (property) address from its components
    street_num  = row.get("STREET_NUM", "").strip()
    half_num    = row.get("STREET_HALF_NUM", "").strip()
    street_name = row.get("FULL_STREET_NAME", "").strip()
    unit_id     = row.get("UNIT_ID", "").strip()

    # Assemble: "9351 PINYON TREE LN B131" style
    parts = [p for p in [street_num, half_num, street_name] if p]
    if unit_id and unit_id not in ("0", ""):
        parts.append(unit_id)
    address = " ".join(parts).strip()

    if not address or len(address) < 5:
        skipped += 1
        continue

    # Owner name: prefer BIZ_NAME (LLC, etc.) over personal name
    biz_name    = row.get("BIZ_NAME", "").strip()
    owner_name1 = row.get("OWNER_NAME1", "").strip()
    owner_name2 = row.get("OWNER_NAME2", "").strip()
    owner_name  = biz_name or owner_name1
    if owner_name2 and not biz_name:
        owner_name = f"{owner_name1} & {owner_name2}"

    # Owner mailing address
    mailing_parts = [
        row.get("OWNER_ADDRESS_LINE1", "").strip(),
        row.get("OWNER_ADDRESS_LINE2", "").strip(),
        row.get("OWNER_CITY", "").strip(),
        row.get("OWNER_STATE", "").strip(),
        row.get("OWNER_ZIPCODE", "").strip(),
    ]
    mailing = ", ".join(p for p in mailing_parts if p)

    # Property city + zip
    prop_city = row.get("PROPERTY_CITY", "Dallas").strip() or "Dallas"
    prop_zip  = row.get("PROPERTY_ZIPCODE", "").strip()[:5]

    # Join RES_DETAIL info
    res_info      = res_lookup.get(account_num, {})
    num_units_raw = res_info.get("NUM_UNITS", "").strip()
    try:
        num_units = int(float(num_units_raw)) if num_units_raw else 1
    except:
        num_units = 1
    property_type = res_info.get("BLDG_CLASS_DESC", "").strip()
    yr_built      = res_info.get("YR_BUILT", "").strip()

    out.append({
        "dcad_account_id":       account_num,
        "address":               address.title(),      # Title Case for display
        "city":                  prop_city.title(),
        "zip":                   prop_zip,
        "owner_name":            owner_name.title() if owner_name else None,
        "owner_mailing_address": mailing or None,
        "property_type":         property_type or None,
        "num_units":             num_units,
        "year_built":            yr_built or None,
    })

print(f"  Built {len(out):,} property records ({skipped:,} skipped — no address)")


# ──────────────────────────────────────────────────────────────
# STEP 4: Quick stats before saving
# ──────────────────────────────────────────────────────────────
multi_family = [p for p in out if (p.get("num_units") or 0) > 1]
has_owner    = [p for p in out if p.get("owner_name")]
dallas_only  = [p for p in out if "dallas" in (p.get("city") or "").lower()]

print(f"\n  Stats:")
print(f"    Total properties:       {len(out):>8,}")
print(f"    With owner name:        {len(has_owner):>8,}")
print(f"    Multi-unit (2+ units):  {len(multi_family):>8,}")
print(f"    City = Dallas:          {len(dallas_only):>8,}")

# Show sample
print(f"\n  Sample record:")
print(json.dumps(out[0] if out else {}, indent=4))


# ──────────────────────────────────────────────────────────────
# STEP 5: Save
# ──────────────────────────────────────────────────────────────
output_file = DATA_DIR / "dcad_properties.json"
with open(output_file, "w") as f:
    json.dump(out, f)

size_mb = output_file.stat().st_size / 1_000_000
print(f"\n✓ Saved → {output_file}")
print(f"  {len(out):,} records  |  {size_mb:.1f} MB")
print(f"\nNext step:")
print(f"  python3 ingest_to_supabase.py")
