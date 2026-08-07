# AGENTS.md

## Cursor Cloud specific instructions

Beacon is a two-service app: a Python/FastAPI backend (`backend/`, port `8000`) and a
Next.js frontend (`frontend/`, port `3000`). SQLite is the default dev DB (file-based, no
separate service). ChromaDB is embedded/on-disk (not a service). Standard commands live in
`README.md`, `docs/AUTH.md`, `frontend/package.json`, and `.env.example`.

### Services and how to run them
- Backend: from `backend/`, run `./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
  Dependencies live in the committed-ignored virtualenv at `backend/venv` (created by the update
  script). Use `./venv/bin/<tool>` rather than relying on an activated shell.
- Frontend: from `frontend/`, run `npm run dev`. It calls the backend via
  `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`); `next.config.js` also rewrites `/api/*`.
- Tests: from `backend/`, run `./venv/bin/pytest tests/ -q` (uses in-memory SQLite and dummy keys
  from `tests/conftest.py`; no external services needed). There is no lint tooling; `npm run build`
  in `frontend/` performs type-checking/linting.

### Non-obvious gotchas
- A repo-root `.env` is required to run the app (copy from `.env.example`). The dev `.env` should
  keep `DATABASE_URL=sqlite:///./immi_assist.db`, and set `SECRET_KEY` + `ENCRYPTION_KEY` to real
  random values. To register accounts through the UI locally, set `ALLOW_PUBLIC_REGISTRATION=true`
  (otherwise `/auth/register` returns 403 unless an admin key is supplied).
- The backend starts fine WITHOUT LLM API keys — it only logs `Missing API keys`. Auth
  (email/password register + login) works with no keys, so the register→authenticated-home flow is
  fully testable offline.
- `/api/v1/health/ready` returns `503 not_ready` until the knowledge base has >=10 policy docs.
  Seeding via `python scripts/ingest_uscis_data.py --yes` (from repo root) requires a valid
  `OPENAI_API_KEY` because ingest generates OpenAI embeddings. Chat/checklist/timeline/RFE also
  need valid LLM keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`) to return real
  answers; without them the app runs but those AI features error.
- Google sign-in on `/login` only appears when `GOOGLE_CLIENT_ID` is set; the email/password path
  works without it.
