# RateMyRental

**Know Before You Sign the Lease**

A Dallas-focused landlord transparency platform that empowers tenants by aggregating public data about rental properties and landlords. Search 858K+ properties by address or landlord name to access eviction history, city complaints, tenant reviews, and AI-powered risk analysis — all free and anonymous.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Data Sources & Ingestion](#data-sources--ingestion)
- [AI Integration](#ai-integration)
- [Red Flag Scoring](#red-flag-scoring)
- [Privacy & Security](#privacy--security)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [License](#license)

---

## Features

### Property Search

Search across 858K+ Dallas properties sourced from the Dallas Central Appraisal District (DCAD) 2025 dataset. Search by street address or landlord/owner name. Results return property address, owner name, zip code, and link to the full property detail page.

### AI Risk Reports

Generate plain-English risk summaries for any property using DeepSeek-R1. The report analyzes eviction filings, 311 complaints, and tenant reviews to produce:

- A 2-3 sentence summary of the property's risk profile
- A risk level classification (low / medium / high)
- 3-5 specific risk factors extracted from the data

Reports are cached in Supabase so subsequent requests for the same property return instantly. Cache is invalidated when a new tenant review is submitted.

### Lease Scanner

Paste lease text (100-50,000 characters) and the AI identifies:

- **Red flags** with severity levels (high / medium / low) — e.g., auto-renewal traps, excessive fees, waived tenant rights, illegal clauses
- **Missing protections** — clauses that should be present but aren't
- **Positive clauses** — tenant-friendly terms worth noting
- **Tenant-friendliness score** (1-10) with a plain-English verdict

### Tenant Rights Chat

A streaming AI chatbot with Dallas/Texas-specific tenant law baked into its system prompt. Covers:

- Security deposits (limits, return timelines, itemized deductions)
- Repair rights and remedies
- Eviction process and timelines
- Landlord entry notice requirements
- Habitability standards
- Retaliation protections

Includes suggestion chips for common questions and links to Dallas Legal Aid resources. Responses stream in real-time via Server-Sent Events.

### Anonymous Tenant Reviews

Tenants can submit reviews with:

- **Star ratings (1-5)** for maintenance responsiveness, lease fairness, and communication
- **Security deposit tracking** — returned (yes / partial / no) and how many days it took
- **Would rent again?** — binary yes/no
- **Optional comments** — free-text field

Reviews are fully anonymous. IP addresses are hashed with SHA-256 for deduplication only (one review per property per IP). No accounts or login required.

### 311 Complaint History

Dallas 311 complaint records linked to properties, covering housing-related issues: overgrown weeds, property maintenance, code violations, and structural problems. Sourced from the Dallas Open Data Socrata API.

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│    Frontend     │────▶│    Backend      │────▶│    Supabase     │
│    (Vercel)     │     │    (Railway)    │     │   (PostgreSQL)  │
│                 │     │                 │     │                 │
│  Next.js 16     │     │  FastAPI        │     │  Properties     │
│  React 19       │     │  Python         │     │  Evictions      │
│  TypeScript     │     │  Uvicorn        │     │  Complaints     │
│  Tailwind CSS 4 │     │                 │     │  Reviews        │
│                 │     │                 │     │  AI Summaries   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
           ┌───────▼───────┐       ┌─────────▼─────────┐
           │   Ollama      │       │   OpenRouter       │
           │   (local dev) │       │   (production)     │
           │               │       │                    │
           │ DeepSeek-R1   │       │ DeepSeek-R1        │
           │ :14b (~9GB)   │       │ API ($0.55/M tok)  │
           └───────────────┘       └────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.10+, Uvicorn, Pydantic 2 |
| Database | Supabase (PostgreSQL) |
| AI | DeepSeek-R1 via Ollama (local) or OpenRouter (production) |
| Rate Limiting | slowapi (token bucket, IP-based) |
| Deployment | Vercel (frontend) + Railway (backend) |

---

## Project Structure

```
RateMyRental/
├── frontend/                        # Next.js application
│   ├── app/
│   │   ├── page.tsx                 # Home page — hero search + feature cards
│   │   ├── search/page.tsx          # Search results — paginated property list
│   │   ├── property/[id]/page.tsx   # Property detail — scores, reviews, AI report
│   │   ├── lease-check/page.tsx     # Lease scanner — paste text, get analysis
│   │   ├── chat/page.tsx            # Tenant rights chatbot — streaming Q&A
│   │   ├── review/[id]/page.tsx     # Review form — star ratings + comments
│   │   ├── layout.tsx               # Root layout — metadata, fonts, nav
│   │   └── globals.css              # Global styles — Tailwind imports
│   ├── public/                      # Static assets
│   ├── package.json                 # Dependencies & scripts
│   ├── tsconfig.json                # TypeScript config
│   ├── next.config.ts               # Next.js config
│   ├── postcss.config.mjs           # PostCSS / Tailwind
│   ├── eslint.config.mjs            # ESLint 9 config
│   ├── .env.local                   # Frontend env (API URL)
│   └── vercel.json                  # Vercel deployment config
│
├── backend/                         # FastAPI application
│   ├── main.py                      # API endpoints, CORS, rate limiting
│   ├── ai_service.py                # AI provider abstraction & prompts
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Example env config
│   ├── Procfile                     # Heroku deployment (alt)
│   └── railway.toml                 # Railway deployment config
│
├── scripts/                         # Data ingestion & processing
│   ├── parse_dcad.py                # Parse DCAD CSV files → JSON
│   ├── download_all_data.py         # Download Eviction Lab + 311 data
│   ├── ingest_to_supabase.py        # Upload all data to Supabase
│   ├── requirements.txt             # Script dependencies
│   └── data/
│       ├── dcad_properties.json     # Parsed DCAD data (858K records)
│       └── DCAD2025_CURRENT/        # Raw DCAD CSV files
│
├── README.md                        # This file
├── DEPLOY.md                        # Deployment guide
└── .gitignore
```

---

## Getting Started

### Prerequisites

- **Node.js 18+** and npm
- **Python 3.10+** and pip
- **Supabase account** — [supabase.com](https://supabase.com) (free tier works)
- **Ollama** (for local AI) — [ollama.com](https://ollama.com) — or an **OpenRouter API key**

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/RateMyRental.git
cd RateMyRental
```

### 2. Set up the database

Create a new Supabase project and set up the following tables:

**properties**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | auto-generated |
| dcad_account_id | text | unique |
| address | text | |
| zip | text | |
| city | text | |
| owner_name | text | |
| owner_mailing_address | text | |
| created_at | timestamptz | default now() |

**evictions**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | auto-generated |
| property_id | uuid (FK) | references properties.id |
| plaintiff_name | text | landlord name |
| filing_date | date | |

**complaints_311**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | auto-generated |
| property_id | uuid (FK) | references properties.id |
| complaint_type | text | |
| status | text | |
| filed_date | date | |

**reviews**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | auto-generated |
| property_id | uuid (FK) | references properties.id |
| landlord_name | text | |
| maintenance_score | int | 1-5 |
| lease_fairness | int | 1-5 |
| communication_score | int | 1-5 |
| deposit_returned | text | yes / partial / no |
| deposit_days | int | nullable |
| would_rent_again | boolean | |
| comments | text | nullable |
| ip_hash | text | SHA-256 of IP |
| submitted_at | timestamptz | default now() |

**ai_summaries**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | auto-generated |
| property_id | uuid (FK) | unique, references properties.id |
| summary | text | AI-generated summary |
| risk_level | text | low / medium / high |
| risk_factors | text[] | array of factors |
| model_used | text | |
| created_at | timestamptz | default now() |

**lease_scans**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | auto-generated |
| ip_hash | text | SHA-256 of IP |
| red_flags_count | int | |
| timestamp | timestamptz | default now() |

You'll also need a Supabase RPC function called `search_properties` for full-text search. See the Supabase dashboard SQL editor to create it.

### 3. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Fill in your Supabase and AI credentials
uvicorn main:app --reload --port 8000
```

The API docs are available at http://localhost:8000/docs (auto-generated by FastAPI).

### 4. Set up the frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```bash
npm run dev
```

The app is available at http://localhost:3000.

### 5. Set up local AI (optional — required for AI features)

```bash
ollama serve
ollama pull deepseek-r1:14b    # ~9GB download
```

Alternatively, set `AI_PROVIDER=openrouter` in `backend/.env` and provide an OpenRouter API key.

### 6. Ingest data

```bash
cd scripts
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `scripts/.env` with your Supabase credentials, then:

```bash
python parse_dcad.py            # Parse DCAD CSV files → JSON
python download_all_data.py     # Fetch Eviction Lab + Dallas 311 data
python ingest_to_supabase.py    # Upload everything to Supabase
```

---

## API Reference

All endpoints are prefixed with the backend URL (default: `http://localhost:8000`).

### `GET /health`

Returns system status including Supabase connection and AI provider availability.

### `GET /api/search?q={query}`

Search properties by address or owner name. Requires minimum 3 characters.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | yes | Search query (address or owner name) |

**Response:** Array of property objects with `id`, `address`, `owner_name`, `zip`.

### `GET /api/property/{id}`

Full property detail including eviction count, complaint count, review average, and red flag score.

**Response:**
```json
{
  "property": { "id": "...", "address": "...", "owner_name": "..." },
  "eviction_count": 3,
  "complaint_count": 7,
  "reviews": [...],
  "red_flag_score": 52,
  "risk_level": "yellow"
}
```

### `POST /api/property/{id}/ai-report`

Generate an AI-powered risk summary for a property. Results are cached.

**Rate limit:** 10 requests/minute per IP.

**Response:**
```json
{
  "summary": "This property has a concerning history...",
  "risk_level": "high",
  "risk_factors": [
    "3 eviction filings in the past 2 years",
    "7 outstanding 311 complaints",
    "Below-average tenant ratings for maintenance"
  ]
}
```

### `POST /api/lease/scan`

Analyze lease text for red flags and missing protections.

**Rate limit:** 5 requests/minute per IP.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lease_text` | string | yes | Lease content (100-50,000 chars) |

**Response:**
```json
{
  "red_flags": [
    { "issue": "Auto-renewal with 60-day notice", "severity": "high", "explanation": "..." }
  ],
  "missing_protections": ["No mold disclosure clause", "..."],
  "positive_clauses": ["30-day repair guarantee", "..."],
  "verdict": "This lease has several concerning terms...",
  "score": 4
}
```

### `POST /api/chat`

Streaming tenant rights Q&A. Returns Server-Sent Events.

**Rate limit:** 20 requests/minute per IP.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | yes | User's question |

**Response:** SSE stream with `data: {"token": "..."}` events.

### `POST /api/review`

Submit an anonymous tenant review.

**Rate limit:** 3 reviews/hour per IP.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `property_id` | uuid | yes | Property to review |
| `landlord_name` | string | yes | Landlord name |
| `maintenance_score` | int | yes | 1-5 |
| `lease_fairness` | int | yes | 1-5 |
| `communication_score` | int | yes | 1-5 |
| `deposit_returned` | string | yes | yes / partial / no |
| `deposit_days` | int | no | Days to return deposit |
| `would_rent_again` | boolean | yes | |
| `comments` | string | no | Free text |

---

## Database Schema

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  properties  │     │  evictions   │     │complaints_311│
│──────────────│     │──────────────│     │──────────────│
│ id (PK)      │◀────│ property_id  │     │ property_id  │──▶ properties.id
│ address      │     │ plaintiff    │     │ complaint_type│
│ owner_name   │     │ filing_date  │     │ status       │
│ zip          │     └──────────────┘     │ filed_date   │
│ city         │                          └──────────────┘
└──────┬───────┘
       │
       ├─────────────────────────────────┐
       │                                 │
┌──────▼───────┐              ┌──────────▼─────┐
│   reviews    │              │  ai_summaries  │
│──────────────│              │────────────────│
│ property_id  │              │ property_id    │ (unique)
│ maintenance  │              │ summary        │
│ lease_fair.  │              │ risk_level     │
│ communication│              │ risk_factors[] │
│ deposit_ret. │              │ model_used     │
│ would_rent   │              └────────────────┘
│ ip_hash      │
│ comments     │
└──────────────┘
```

All foreign keys reference `properties.id`. The `ai_summaries` table has a unique constraint on `property_id` (one cached report per property, upserted on regeneration).

---

## Data Sources & Ingestion

### DCAD (Dallas Central Appraisal District)

- **Records:** 858,618 properties
- **Data:** Property address, owner name, owner mailing address, zip code
- **Format:** Multiple CSV files in `scripts/data/DCAD2025_CURRENT/`
- **Script:** `scripts/parse_dcad.py` — uses pandas to join CSV files and output `dcad_properties.json`

### Eviction Lab (Princeton University)

- **Data:** Court eviction filing records — hotspots, monthly trends, claims, demographics
- **Key fields:** Address, plaintiff (landlord) name, filing counts
- **Script:** `scripts/download_all_data.py` — downloads CSV files directly

### Dallas 311 Open Data

- **Data:** Housing-related city complaints (property maintenance, code violations, structural issues, overgrown weeds)
- **API:** Socrata API (no key required, 1,000 rows per request, up to 50K records fetched)
- **Script:** `scripts/download_all_data.py` — paginated JSON downloads

### Running ingestion

```bash
cd scripts
source venv/bin/activate

# Step 1: Parse raw DCAD CSVs into JSON
python parse_dcad.py

# Step 2: Download external datasets
python download_all_data.py

# Step 3: Upload everything to Supabase
python ingest_to_supabase.py
```

---

## AI Integration

The backend supports two AI providers, selected via the `AI_PROVIDER` environment variable:

### Local development — Ollama

- **Model:** DeepSeek-R1:14b (~9GB)
- **Endpoint:** `http://localhost:11434`
- **Pros:** Free, no API key, works offline
- **Cons:** Requires ~10GB disk + decent GPU/CPU, slower

### Production — OpenRouter

- **Model:** `deepseek/deepseek-r1-0528:free` (free tier) or `deepseek/deepseek-r1` (~$0.55/M tokens)
- **API:** OpenAI-compatible REST endpoint
- **Pros:** No local hardware requirements, fast
- **Cons:** Requires API key, rate limits on free tier

### Provider fallback

If `AI_PROVIDER` is set to `ollama` but the local server isn't running, the backend logs a warning. There is no automatic fallback — set the provider explicitly for your environment.

### AI features

| Feature | Prompt strategy | Caching |
|---------|----------------|---------|
| Risk report | Property data → structured JSON (summary, risk level, factors) | Cached in `ai_summaries` table, invalidated on new review |
| Lease scanner | Lease text (truncated to 8K chars) → structured JSON (flags, protections, score) | Not cached |
| Tenant chat | System prompt with Dallas/TX law context → streaming tokens | Not cached |

The AI service strips `<think>...</think>` tags from DeepSeek reasoning model outputs and extracts JSON via regex with fallback to plain text.

---

## Red Flag Scoring

Each property gets a composite risk score (0-100) calculated as:

```
score = (eviction_count × 10) + (complaint_count × 2) + (rating_penalty × 10)
```

Where `rating_penalty` is derived from the average tenant review rating:
- 5 stars → 0 penalty
- 1 star → 2.5 penalty (scaled)

The score is capped at 100 and mapped to a color:

| Score | Color | Risk Level |
|-------|-------|------------|
| 0-24 | Green | Low |
| 25-59 | Yellow | Medium |
| 60-100 | Red | High |

---

## Privacy & Security

- **No user accounts** — the platform is fully anonymous with no login or session state
- **IP hashing** — IP addresses are SHA-256 hashed before storage; plain IPs are never persisted
- **Review deduplication** — one review per property per IP hash
- **Lease scan logging** — only the IP hash and red flag count are stored (lease text is never saved)
- **Rate limiting** — per-IP token bucket via slowapi on all endpoints
- **CORS** — all origins allowed (public API)
- **No PII collection** — no names, emails, or personal data collected from users

---

## Environment Variables

### Backend (`backend/.env`)

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key

AI_PROVIDER=ollama                          # or openrouter
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:14b
OPENROUTER_API_KEY=sk-or-your-key-here      # production only
OPENROUTER_MODEL=deepseek/deepseek-r1-0528:free
```

### Frontend (`frontend/.env.local`)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Scripts (`scripts/.env`)

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
```

---

## Deployment

See [DEPLOY.md](DEPLOY.md) for full deployment instructions covering:

- **Frontend** → Vercel (auto-deploy from GitHub)
- **Backend** → Railway (auto-detected via `railway.toml`)
- **Database** → Supabase (managed PostgreSQL)
- **AI** → OpenRouter (no GPU needed in production)

Quick reference:
- Frontend URL: `https://ratemyrental.vercel.app`
- API docs: `https://your-app.railway.app/docs`
- Health check: `https://your-app.railway.app/health`

---

## License

All rights reserved.
