# Axiom OS v2 — Lamora Healthcare Lead Generation Platform

AI-powered lead generation: 10 agents scrape, score, enrich and draft
outreach for care leads. Hybrid mode — fully auto for scraping/scoring,
approval gate for outreach.

## Quick Start

### Backend
```bash
cd backend
cp .env.example .env        # fill in all keys
pip install -r requirements.txt
playwright install chromium
redis-server &              # or use Redis Cloud
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm install && npm run dev
```

Open http://localhost:3000 → Configure → Run Pipeline

## Pipeline Stages
1. Lead Scraper — Playwright scrapes Google, forums, directories, Bark, LinkedIn, NHS/LA, Facebook
2. Lead Intelligence — scores every lead 0-100
3. Lead Enrichment — enriches qualifying leads for CRM
4. Urgency Detection — flags immediate escalations
5. Outreach Agent — drafts GDPR-compliant messages ← APPROVAL GATE
6. Nurture Agent — plans follow-up sequences
7. Booking Agent — flags assessment-ready leads
8. CRM Manager — pipeline health check
9. CEO Agent — strategic briefing

## API Routes (FastAPI)
- POST /api/pipeline/run — start full pipeline
- GET  /api/pipeline/stream/{id} — SSE live updates
- GET  /api/pipeline/status/{id} — poll status
- GET  /api/leads — CRM leads
- POST /api/agents/run — run single agent
- GET  /api/outreach — approval queue
- POST /api/outreach/{id}/approve — approve draft
- POST /api/outreach/{id}/send — send via Resend
- GET  /api/dashboard/stats — KPI data

## Infrastructure
- Supabase — PostgreSQL + Auth (run supabase-schema.sql)
- Redis — job queues + real-time pipeline status
- Resend — email sending post-approval
- Anthropic Claude — all 10 agent brains

## Deploy
Backend: Railway or Render (set env vars)
Frontend: Vercel (set NEXT_PUBLIC_API_URL)
