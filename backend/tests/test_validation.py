"""Production config validation tests."""

import os
import pytest

from app.core.config import Settings, get_settings
from app.core.validation import validate_production_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_production_rejects_default_secrets():
    settings = Settings(
        app_env="production",
        secret_key="change-this-in-production",
        admin_api_key="change-this-admin-key",
        openai_api_key="sk-your-openai-key",
        anthropic_api_key="test",
        google_api_key="test",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_settings(settings)


def test_development_allows_defaults():
    settings = Settings(app_env="development", secret_key="change-this-in-production")
    validate_production_settings(settings)
