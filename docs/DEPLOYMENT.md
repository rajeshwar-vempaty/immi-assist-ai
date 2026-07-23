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

- **Users**: Google sign-in (`POST /api/v1/auth/google`) or `AUTH_DEV_MODE` email login
- **Session**: JWT httpOnly cookie + optional Bearer token
- **Admin**: `POST /api/v1/admin/scrape`, `POST /api/v1/admin/ingest?scrape=true` with `X-Admin-Key`
- See [AUTH.md](./AUTH.md) and [PRODUCTION.md](./PRODUCTION.md)

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
| `GET /api/v1/health/live` | Process alive (200) |
| `GET /api/v1/health/ready` | DB + KB ready (**503** until ready) |
| `GET /api/v1/health` | Legacy summary |

## Production (Docker)

See **[PRODUCTION.md](./PRODUCTION.md)** for the full checklist.

```bash
cp .env.example .env
# Required: SECRET_KEY, ENCRYPTION_KEY, ADMIN_API_KEY, GOOGLE_CLIENT_ID,
# AUTH_DEV_MODE=false, LLM keys, POSTGRES_PASSWORD, SITE_ADDRESS, ACME_EMAIL,
# PUBLIC_API_URL, CORS_ORIGINS

# Recommended (Postgres)
docker compose -f docker-compose.prod.yml up --build -d

# Pilot only (SQLite, 1 worker)
docker compose -f docker-compose.prod.sqlite.yml up --build -d
```

### Architecture

| Service | Role |
|---------|------|
| `caddy` | Reverse proxy, TLS (ports 80/443); public `/api/*` + frontend only |
| `db` | Postgres 16 (prod compose) |
| `backend` | FastAPI API (internal) |
| `frontend` | Next.js UI (internal) |
| `scheduler` | Weekly scrape + ingest refresh |
| `prometheus` | Optional internal metrics (`--profile metrics`; no host port) |

- App URL: `http://localhost` (local) or `https://$SITE_ADDRESS`
- API docs: disabled in production (404 at edge)
- Metrics: internal Docker network only

### Observability

- **Prometheus**: internal only (`docker compose --profile metrics up`); scrapes `backend:8000/metrics`
- **Sentry**: set `SENTRY_DSN` in `.env` for error tracking
- **LLM metrics**: `llm_requests_total`, `llm_request_duration_seconds`

### Scheduled refresh

The `scheduler` service runs `scripts/scheduled_refresh.py` every `INGEST_INTERVAL_HOURS` (default 168 = weekly).

- Backend runs migrations on start
- Set `RUN_INGEST_ON_START=true` to seed ChromaDB when empty
- Volumes: `chroma_data`, `postgres_data` (or `sqlite_data`), `caddy_data`, `prometheus_data`

## CI

GitHub Actions runs backend `pytest` and frontend `npm run build` on push/PR.

## Rate Limits

| Tier | Default daily limit |
|------|---------------------|
| free (anonymous) | 5 |
| starter (API key) | 100 |

Configure via `FREE_TIER_DAILY_LIMIT` and `STARTER_TIER_DAILY_LIMIT`.
