# Public launch checklist

Beacon is ready for a **controlled public rollout** once this checklist is done.
Product phases 3–6 (checklist/RFE depth, streaming chat, case profile, scale polish)
can continue **after** launch; they are not hard blockers for an invite-only or
limited public pilot.

## Recommended launch shape

1. **Invite-only / private pilot** (registration closed) with a scraped KB  
2. Smoke-test with real users on BYOK chat  
3. Turn on `REQUIRE_SCRAPED_KB=true` after the first successful scrape  
4. Optionally open registration (`ALLOW_PUBLIC_REGISTRATION=true`)

Do **not** open unrestricted signup on a sample-only knowledge base.

## A. Before DNS / domain

- [ ] Merge latest `main` (Phase 0–2 + review fixes)
- [ ] Host with Docker, ports 80/443 open, domain DNS → server
- [ ] Generate secrets (`SECRET_KEY`, `ENCRYPTION_KEY`, `ADMIN_API_KEY`, `POSTGRES_PASSWORD`)
- [ ] Google OAuth Web client: authorized JS origin = `https://YOUR_DOMAIN`
- [ ] Platform LLM keys present (embeddings + checklist/timeline/RFE)
- [ ] Decide signup mode: leave `ALLOW_PUBLIC_REGISTRATION=false` for invite-only

## B. Production `.env` (minimum)

```bash
APP_ENV=production
DEBUG=false
AUTH_DEV_MODE=false
ALLOW_SQLITE_IN_PRODUCTION=false
ALLOW_PUBLIC_REGISTRATION=false
REQUIRE_SCRAPED_KB=false          # flip to true AFTER first scraped ingest
RUN_INGEST_ON_START=true          # seeds sample so /health/ready can pass
RUN_REFRESH_ON_START=true         # optional: scheduler scrapes on first boot

SITE_ADDRESS=immiassist.yourdomain.com
ACME_EMAIL=ops@yourdomain.com
PUBLIC_API_URL=https://immiassist.yourdomain.com/api/v1
CORS_ORIGINS=https://immiassist.yourdomain.com

GOOGLE_CLIENT_ID=...
SECRET_KEY=...
ENCRYPTION_KEY=...
ADMIN_API_KEY=...
POSTGRES_PASSWORD=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
# SENTRY_DSN=...                  # strongly recommended for public traffic
```

Full table: [PRODUCTION.md](./PRODUCTION.md). Auth: [AUTH.md](./AUTH.md).

## C. Deploy

```bash
cp .env.example .env
# fill values from section B

docker compose -f docker-compose.prod.yml up -d --build

# Optional internal metrics
docker compose -f docker-compose.prod.yml --profile metrics up -d
```

Wait until backend is healthy (`/api/v1/health/ready` → 200).

## D. Knowledge base (trust unlock)

Sample ingest is fine for **bootstrapping** readiness. For public users, scrape then re-ingest:

```bash
# On the host / in the backend container (network required)
python scripts/scrape_uscis_data.py --max-chapters 80
python scripts/ingest_uscis_data.py --yes --require-scraped
```

Or trigger via admin (with `X-Admin-Key`):

```bash
curl -X POST "https://YOUR_DOMAIN/api/v1/admin/ingest?scrape=true" \
  -H "X-Admin-Key: $ADMIN_API_KEY"
```

Then set in `.env` and recreate backend:

```bash
REQUIRE_SCRAPED_KB=true
docker compose -f docker-compose.prod.yml up -d backend
```

Confirm health payload shows `"knowledge_base_mode": "scraped"`.

## E. Smoke test

```bash
./scripts/public_launch_smoke.sh https://YOUR_DOMAIN
```

Manual:

- [ ] `GET /api/v1/health/live` → 200  
- [ ] `GET /api/v1/health/ready` → 200, mode `scraped` when required  
- [ ] `GET /docs` → 404  
- [ ] `GET /metrics` → 404 at the public edge  
- [ ] `/login` → Google sign-in works  
- [ ] Settings → save a BYOK key → Chat returns an answer with sources  
- [ ] Timeline Form → Category → Office returns Live or Cached estimate  
- [ ] Checklist + RFE tabs return structured output + disclaimer  

## F. Go-live communications

- [ ] Site copy still says **informational guidance, not legal advice**
- [ ] Users understand chat is **BYOK** (they supply a provider API key)
- [ ] Invite list / waitlist process if registration stays closed
- [ ] Backup schedule: `python scripts/backup_data.py --output ./backups`
- [ ] On-call path for auth outages and scrape failures (Sentry + admin scrape)

## G. After launch (product backlog)

| Phase | Focus |
|-------|--------|
| **3** | Checklist / RFE depth (stronger grounding, less generic outputs) |
| **4** | Streaming chat + cancel |
| **5** | Case profile (visa, forms, priority date, office reused across tabs) |
| **6** | Scale polish (tighter rate limits, hosted free tier if desired, multi-tenant ops) |

## Related

- [PRODUCTION.md](./PRODUCTION.md) — secrets, surface hardening, compose  
- [DEPLOYMENT.md](./DEPLOYMENT.md) — local + Docker overview  
- [AUTH.md](./AUTH.md) — Google OAuth and sessions  
