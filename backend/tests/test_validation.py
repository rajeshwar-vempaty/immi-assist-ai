"""Production config validation tests."""

import pytest

from app.core.config import Settings, get_settings
from app.core.validation import validate_production_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _prod_kwargs(**overrides):
    base = dict(
        app_env="production",
        secret_key="prod-secret-key-not-a-default-value",
        encryption_key="prod-encryption-key-distinct-from-secret",
        admin_api_key="prod-admin-key-not-default",
        auth_dev_mode=False,
        google_client_id="1234567890-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com",
        openai_api_key="sk-live-openai",
        anthropic_api_key="sk-ant-live",
        google_api_key="AIza-live-google",
        database_url="postgresql+psycopg://immi:pass@db:5432/immi_assist",
        allow_sqlite_in_production=False,
    )
    base.update(overrides)
    return base


def test_production_rejects_default_secrets():
    settings = Settings(
        **_prod_kwargs(
            secret_key="change-this-in-production",
            admin_api_key="change-this-admin-key",
            openai_api_key="sk-your-openai-key",
        )
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_settings(settings)


def test_production_rejects_auth_dev_mode():
    settings = Settings(**_prod_kwargs(auth_dev_mode=True))
    with pytest.raises(RuntimeError, match="AUTH_DEV_MODE"):
        validate_production_settings(settings)


def test_production_requires_google_client_id():
    settings = Settings(**_prod_kwargs(google_client_id=""))
    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_ID"):
        validate_production_settings(settings)


def test_production_requires_encryption_key():
    settings = Settings(**_prod_kwargs(encryption_key=None))
    with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
        validate_production_settings(settings)


def test_production_rejects_sqlite_without_override():
    settings = Settings(
        **_prod_kwargs(
            database_url="sqlite:////app/data/immi_assist.db",
            allow_sqlite_in_production=False,
        )
    )
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_production_settings(settings)


def test_production_allows_sqlite_with_override():
    settings = Settings(
        **_prod_kwargs(
            database_url="sqlite:////app/data/immi_assist.db",
            allow_sqlite_in_production=True,
        )
    )
    validate_production_settings(settings)


def test_production_accepts_secure_config():
    settings = Settings(**_prod_kwargs())
    validate_production_settings(settings)


def test_development_allows_defaults():
    settings = Settings(app_env="development", secret_key="change-this-in-production")
    validate_production_settings(settings)
