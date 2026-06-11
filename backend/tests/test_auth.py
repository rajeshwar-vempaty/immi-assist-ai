"""Auth hardening tests."""

import os
from unittest.mock import patch

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_register_blocked_without_admin(client):
    os.environ["ALLOW_PUBLIC_REGISTRATION"] = "false"
    get_settings.cache_clear()

    response = client.post("/api/v1/auth/register", json={"email": "test@example.com"})
    assert response.status_code == 403


def test_register_with_admin_key(client):
    os.environ["ALLOW_PUBLIC_REGISTRATION"] = "false"
    os.environ["ADMIN_API_KEY"] = "test-admin-key"
    get_settings.cache_clear()

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "admin-created@example.com", "tier": "starter"},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "starter"
    assert data["api_key"].startswith("immi_")


def test_public_registration_free_tier_only(client):
    os.environ["ALLOW_PUBLIC_REGISTRATION"] = "true"
    os.environ["ADMIN_API_KEY"] = "test-admin-key"
    get_settings.cache_clear()

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "public@example.com", "tier": "starter"},
    )
    assert response.status_code == 200
    assert response.json()["tier"] == "free"


def test_revoke_key_requires_auth(client):
    response = client.delete("/api/v1/auth/keys/fake-id")
    assert response.status_code == 401
