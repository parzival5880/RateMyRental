# RateMyRental — Deployment Guide

## Architecture

```
Frontend (Vercel)  →  Backend (Railway)  →  Supabase (DB)
Next.js                FastAPI                 PostgreSQL
                           ↓
                    AI: Ollama (dev)
                    AI: OpenRouter (prod)
```

---

## 1. Backend → Railway

### Setup
1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select the repo root, set **Root Directory** to `backend/`
3. Railway auto-detects `railway.toml` and uses nixpacks

### Environment Variables (set in Railway dashboard)
```
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here

# AI — use OpenRouter in production (no GPU needed, ~$0.55/M tokens)
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-YOUR_KEY_HERE
OPENROUTER_MODEL=deepseek/deepseek-r1-0528:free
```

### Get an OpenRouter key (free tier available)
1. Go to [openrouter.ai](https://openrouter.ai) → Sign up
2. Keys → Create API key
3. `deepseek/deepseek-r1-0528:free` is free with rate limits
4. For production: `deepseek/deepseek-r1` is ~$0.55/M tokens

---

## 2. Frontend → Vercel

### Setup
1. Go to [vercel.com](https://vercel.com) → New Project → Import GitHub repo
2. Set **Root Directory** to `frontend/`
3. Framework: Next.js (auto-detected)

### Environment Variables (set in Vercel dashboard)
```
NEXT_PUBLIC_API_URL=https://YOUR-RAILWAY-APP.railway.app
```

---

## 3. Local Development

### Start backend
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Start frontend
```bash
cd frontend
npm run dev
```

### AI model (local)
```bash
# Ollama runs automatically if installed
ollama serve  # if not already running
# Model already pulled: deepseek-r1:14b (9GB)
```

---

## Data Status
- **DCAD Properties**: 858,618 records ✅ (fully ingested)
- **Eviction Lab**: run `python scripts/download_all_data.py` to fetch
- **Dallas 311**: run `python scripts/download_all_data.py` to fetch

### Re-run ingestion
```bash
cd scripts
source venv/bin/activate
python ingest_to_supabase.py
```

---

## URLs (after deploy)
- Frontend: `https://ratemyrental.vercel.app`
- Backend API: `https://your-app.railway.app`
- API Docs: `https://your-app.railway.app/docs` (FastAPI auto-generated)
- Health: `https://your-app.railway.app/health`
