# Authentication & user API keys

## Overview

Beacon uses **Google Identity Services** for sign-in (plus optional `AUTH_DEV_MODE` email login for local development). Sessions are JWTs delivered as an httpOnly cookie (`immi_session`) and optionally mirrored in `sessionStorage` for `Authorization: Bearer` calls.

Provider API keys (OpenAI, Anthropic, Gemini, Groq) are stored **encrypted at rest** in SQLite and never returned in full to the browser.

## Environment variables

Add these to `.env` (see also `.env.example`):

```bash
# Required in production
SECRET_KEY=long-random-string
ENCRYPTION_KEY=another-long-random-string   # Fernet key material (derived via SHA-256)

# Google OAuth (Web client ID from Google Cloud Console)
GOOGLE_CLIENT_ID=1234567890-xxxx.apps.googleusercontent.com

# Local development without Google
AUTH_DEV_MODE=true

# Platform keys still used for embeddings / checklist-timeline-RFE structured tools
OPENAI_API_KEY=...
```

## Configure Google sign-in

1. Open [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials.
2. Create an **OAuth 2.0 Client ID** of type **Web application**.
3. Add authorized JavaScript origins:
   - `http://localhost:3000`
   - your production frontend origin
4. Copy the Client ID into `GOOGLE_CLIENT_ID` in `.env`.
5. Restart the backend. The login page loads GIS and renders **Continue with Google**.
6. Ensure `CORS_ORIGINS` includes your frontend origin.

## Security decisions

| Topic | Decision |
|-------|----------|
| Session | JWT (HS256) in httpOnly cookie + optional Bearer header |
| Provider keys | Fernet encryption (key derived from `ENCRYPTION_KEY` or `SECRET_KEY`) |
| Browser storage | No provider keys in localStorage/sessionStorage |
| API responses | Masked only (`sk-****abcd`) |
| Logout | Clears cookie + client storage/UI; **does not** delete DB conversations |
| Chat BYOK | `/chat` uses the authenticated user's decrypted provider key |
| Other tools | Checklist / timeline / RFE still use platform env keys (embeddings/RAG) |

## Running locally

```bash
# Backend
cd backend
pip install -r requirements.txt
export AUTH_DEV_MODE=true
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 → login (dev email or Google) → Settings → add a provider key → Chat.

## Tests

```bash
cd backend
pytest -q
```

Covered scenarios include Google login (mocked), protected routes, User A / User B conversation isolation, encrypted credential masking, and missing-key chat errors.

## Migrations

New installs: `init_db()` creates tables via SQLAlchemy `create_all`.

Existing Alembic deployments:

```bash
cd backend
alembic upgrade head
```

Migration `002_auth_credentials_conversations.py` adds user profile columns, `user_provider_credentials`, `user_preferences`, `conversations`, and `messages`.
