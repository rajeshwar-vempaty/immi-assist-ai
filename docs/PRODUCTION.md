# Production readiness checklist

Use this before pointing real users at a deployment.

## 1. Secrets and auth (required)

Generate strong values and put them in `.env` (never commit):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

| Variable | Requirement |
|----------|-------------|
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `SECRET_KEY` | random, not an example default |
| `ENCRYPTION_KEY` | **different** random value from `SECRET_KEY` |
| `ADMIN_API_KEY` | random; used for `/admin/*` and optional metrics |
| `AUTH_DEV_MODE` | **`false`** |
| `GOOGLE_CLIENT_ID` | OAuth Web client ID from Google Cloud Console |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` | real platform keys (embeddings + checklist/timeline/RFE) |
| `CORS_ORIGINS` | your frontend origin(s), e.g. `https://immiassist.example.com` |
| `SITE_ADDRESS` | domain for Caddy TLS, e.g. `immiassist.example.com` |
| `ACME_EMAIL` | email for Let’s Encrypt |
| `PUBLIC_API_URL` | `https://immiassist.example.com/api/v1` |
| `POSTGRES_PASSWORD` | required for `docker-compose.prod.yml` |

Startup **refuses to boot** in production if secrets, Google client ID, or `AUTH_DEV_MODE` are wrong.

## 2. Google OAuth (GIS)

1. Google Cloud Console → APIs & Services → Credentials
2. Create **OAuth 2.0 Client ID** → **Web application**
3. Authorized JavaScript origins:
   - `https://immiassist.example.com`
   - (local) `http://localhost:3000`
4. Copy Client ID → `GOOGLE_CLIENT_ID`
5. Tokens must have `email_verified=true` (enforced in `google_auth.py`)

## 3. Public surface (already hardened in code/compose)

| Surface | Behavior |
|---------|----------|
| `/api/*` | Public via Caddy |
| `/docs`, `/redoc`, `/openapi.json` | Disabled in production FastAPI + blocked at Caddy |
| `/metrics` | Not proxied by Caddy; scrape only on Docker network. With `METRICS_REQUIRE_ADMIN=true`, needs `X-Admin-Key` |
| Prometheus `:9090` | **Not published** to the host (internal `expose` + optional `--profile metrics`) |
| `/api/v1/admin/*` | Requires `X-Admin-Key`; call only from trusted operators/CI |

## 4. Readiness

`GET /api/v1/health/ready` returns **503** until:

- DB responds to `SELECT 1`
- Policy KB docs ≥ `MIN_KNOWLEDGE_BASE_DOCUMENTS`
- Processing-times collection has at least one doc

Docker healthchecks use `-f` so containers stay unhealthy until ingest succeeds.

## 5. Database

**Recommended:** Postgres via `docker-compose.prod.yml`

```bash
# .env
POSTGRES_PASSWORD=...long-random...
POSTGRES_USER=immi
POSTGRES_DB=immi_assist

docker compose -f docker-compose.prod.yml up -d --build
```

**Pilot only:** SQLite + **one** worker

```bash
docker compose -f docker-compose.prod.sqlite.yml up -d --build
```

That sets `ALLOW_SQLITE_IN_PRODUCTION=true` and `UVICORN_WORKERS=1`.

## 6. Deploy commands

```bash
cp .env.example .env
# fill production values from the table above

# Postgres (preferred)
docker compose -f docker-compose.prod.yml up -d --build

# Optional metrics stack (internal only)
docker compose -f docker-compose.prod.yml --profile metrics up -d

# Backups (schedule this)
python scripts/backup_data.py --output ./backups
```

## 7. Smoke test

1. Open site → `/login` → Continue with Google  
2. Settings → add a provider API key → Chat  
3. Confirm `curl -i https://YOUR_HOST/api/v1/health/ready` → 200  
4. Confirm `curl -i https://YOUR_HOST/docs` → 404  
5. Confirm `curl -i https://YOUR_HOST/metrics` → 404 (edge)

## Related

- Auth details: [AUTH.md](./AUTH.md)
- Broader deploy notes: [DEPLOYMENT.md](./DEPLOYMENT.md)
