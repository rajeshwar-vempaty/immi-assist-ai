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


def validate_production_settings(settings: Settings) -> None:
    """Raise on startup if production is configured with insecure defaults."""
    if settings.app_env != "production":
        return

    errors: list[str] = []

    if settings.secret_key in INSECURE_SECRET_KEYS:
        errors.append("SECRET_KEY must be set to a unique random value in production")

    if not settings.admin_api_key or settings.admin_api_key in INSECURE_ADMIN_KEYS:
        errors.append("ADMIN_API_KEY must be set in production")

    for name, value in (
        ("OPENAI_API_KEY", settings.openai_api_key),
        ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
        ("GOOGLE_API_KEY", settings.google_api_key),
    ):
        if not value or value.startswith("sk-your") or value.startswith("your-"):
            errors.append(f"{name} must be configured in production")

    if errors:
        raise RuntimeError(
            "Production configuration errors:\n- " + "\n- ".join(errors)
        )
