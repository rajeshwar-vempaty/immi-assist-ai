"""
Core configuration — loads environment variables and manages app settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "ImmiAssist AI"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-this-in-production"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Encryption for provider API keys at rest
    encryption_key: Optional[str] = None

    # JWT session
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 168
    session_cookie_name: str = "immi_session"

    # Google OAuth (Identity Services client ID)
    google_client_id: str = ""
    # Dev-only: allow email/name login without Google token
    auth_dev_mode: bool = False

    # Platform/fallback LLM API Keys (embeddings / optional system fallback)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # Model Configuration
    classifier_model: str = "gemini-2.0-flash"
    reasoning_model: str = "claude-sonnet-4-20250514"
    structured_model: str = "gemini-2.0-flash"
    embedding_model: str = "text-embedding-3-small"

    # Database
    database_url: str = "sqlite:///./immi_assist.db"
    # Pilot escape hatch: SQLite in production requires single worker and backups
    allow_sqlite_in_production: bool = False

    # API surface
    # When None: docs enabled outside production. Set EXPOSE_API_DOCS=true/false to override.
    expose_api_docs: bool | None = None
    # Require X-Admin-Key for /metrics. Keep false when Prometheus scrapes on the private network.
    metrics_require_admin: bool = False

    # Vector Store — relative paths resolve against backend/
    chroma_persist_dir: str = "./data/chroma_db"
    pinecone_api_key: Optional[str] = None
    pinecone_index: Optional[str] = None

    # Rate Limiting
    free_tier_daily_limit: int = 5
    starter_tier_daily_limit: int = 100

    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    # Admin
    admin_api_key: Optional[str] = None

    # Auth hardening
    allow_public_registration: bool = False
    max_api_keys_per_user: int = 3
    max_registrations_per_ip_per_day: int = 3

    # Knowledge base
    min_knowledge_base_documents: int = 10

    # LLM resilience
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2

    # Observability
    metrics_enabled: bool = True
    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.1

    # Scheduler
    ingest_interval_hours: int = 168

    # Reverse proxy / TLS
    site_address: str = "localhost"
    public_api_url: str = "http://localhost:8000/api/v1"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if self.site_address and self.site_address not in (":80", "localhost"):
            origins.extend(
                [
                    f"https://{self.site_address}",
                    f"http://{self.site_address}",
                ]
            )
        return list(dict.fromkeys(origins))

    @property
    def resolved_chroma_dir(self) -> str:
        path = Path(self.chroma_persist_dir)
        if not path.is_absolute():
            path = _BACKEND_ROOT / path
        return str(path.resolve())

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — loaded once at startup."""
    return Settings()
