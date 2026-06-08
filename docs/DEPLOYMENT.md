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
- **Registered**: `POST /api/v1/auth/register` with `X-Admin-Key` header (production default)
- **Dev only**: Set `ALLOW_PUBLIC_REGISTRATION=true` for self-service free-tier keys (capped per IP)
- **Key management**: `GET /auth/keys`, `POST /auth/keys`, `DELETE /auth/keys/{id}` (authenticated)
- **Admin**: `POST /api/v1/admin/scrape`, `POST /api/v1/admin/ingest?scrape=true` with `X-Admin-Key`

## Data Pipeline

```bash
# Scrape USCIS policy + forms (requires network)
python scripts/scrape_uscis_data.py

# Ingest into ChromaDB (use --scrape to scrape first)
python scripts/ingest_uscis_data.py --yes --scrape
```

## Backups

```bash
python scripts/backup_data.py --output ./backups
```

Restores: copy `immi_assist.db` and `chroma_db/` back to `backend/` paths.

## Health Checks

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health/live` | Process alive |
| `GET /api/v1/health/ready` | DB + KB ≥ `MIN_KNOWLEDGE_BASE_DOCUMENTS` + processing times |
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
