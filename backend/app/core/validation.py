"""Production configuration validation."""

from app.core.config import Settings

INSECURE_SECRET_KEYS = {
    "change-this-in-production",
    "change-this-to-a-random-secret-key",
}
INSECURE_ADMIN_KEYS = {
    "change-this-admin-key",
    "",
}
INSECURE_ENCRYPTION_KEYS = {
    None,
    "",
    "change-this-to-another-random-secret",
    "dev-encryption-key-change-me-32b!",
    "test-encryption-key-32-characters!",
}


def validate_production_settings(settings: Settings) -> None:
    """Raise on startup if production is configured with insecure defaults."""
    if settings.app_env != "production":
        return

    errors: list[str] = []

    if settings.secret_key in INSECURE_SECRET_KEYS:
        errors.append("SECRET_KEY must be set to a unique random value in production")

    if not settings.admin_api_key or settings.admin_api_key in INSECURE_ADMIN_KEYS:
        errors.append("ADMIN_API_KEY must be set in production")

    enc = settings.encryption_key
    if enc in INSECURE_ENCRYPTION_KEYS or enc == settings.secret_key:
        errors.append(
            "ENCRYPTION_KEY must be set to a dedicated random value "
            "(do not reuse SECRET_KEY or example defaults)"
        )

    if settings.auth_dev_mode:
        errors.append("AUTH_DEV_MODE must be false in production")

    if not settings.google_client_id or len(settings.google_client_id) < 20:
        errors.append("GOOGLE_CLIENT_ID must be configured for Google sign-in in production")

    for name, value in (
        ("OPENAI_API_KEY", settings.openai_api_key),
        ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
        ("GOOGLE_API_KEY", settings.google_api_key),
    ):
        if not value or value.startswith("sk-your") or value.startswith("your-"):
            errors.append(f"{name} must be configured in production")

    if "sqlite" in settings.database_url.lower() and settings.allow_sqlite_in_production is False:
        errors.append(
            "DATABASE_URL must use Postgres in production "
            "(or set ALLOW_SQLITE_IN_PRODUCTION=true for single-worker pilots only)"
        )

    if errors:
        raise RuntimeError(
            "Production configuration errors:\n- " + "\n- ".join(errors)
        )
