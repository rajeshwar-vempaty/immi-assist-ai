"""
Core configuration — loads environment variables and manages app settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "ImmiAssist AI"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-this-in-production"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # LLM API Keys
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

    # Vector Store
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — loaded once at startup."""
    return Settings()
