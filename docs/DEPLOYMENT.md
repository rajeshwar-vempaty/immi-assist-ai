# ImmiAssist AI — Deployment Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`

## Local Development

```bash
# From repository root
cp .env.example .env
# Edit .env with your API keys

./setup.sh

# Ingest knowledge base (required before readiness check passes)
python scripts/ingest_uscis_data.py --yes

# Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev
```

- API: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Database (SQLite)

- Default path: `./immi_assist.db` (backend working directory)
- Tables are created on startup via `init_db()`
- Migrations: `cd backend && alembic upgrade head`

## API Authentication

- **Anonymous**: Send `X-Session-ID` header (returned on first response) for rate limiting
- **Registered**: `POST /api/v1/auth/register` → use returned `api_key` as `X-API-Key` header
- **Admin ingest**: Set `ADMIN_API_KEY` in `.env`, call `POST /api/v1/admin/ingest` with `X-Admin-Key`

## Health Checks

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health/live` | Process alive |
| `GET /api/v1/health/ready` | DB + knowledge base populated |
| `GET /api/v1/health` | Legacy summary |

## Production (Docker)

```bash
cp .env.example .env
# Set production values: SECRET_KEY, ADMIN_API_KEY, API keys

docker compose -f docker-compose.prod.yml up --build
```

- Backend runs migrations on start
- Set `RUN_INGEST_ON_START=true` to seed ChromaDB when empty
- Volumes: `chroma_data`, `sqlite_data`

## CI

GitHub Actions runs backend `pytest` and frontend `npm run build` on push/PR.

## Rate Limits

| Tier | Default daily limit |
|------|---------------------|
| free (anonymous) | 5 |
| starter (API key) | 100 |

Configure via `FREE_TIER_DAILY_LIMIT` and `STARTER_TIER_DAILY_LIMIT`.
