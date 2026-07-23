"""Auth endpoint tests — Google/dev login and session protection."""

from unittest.mock import patch

from app.core.config import get_settings
from app.core.exceptions import AuthError


def test_dev_login_disabled_when_flag_off(client):
    settings = get_settings()
    original = settings.auth_dev_mode
    settings.auth_dev_mode = False
    try:
        response = client.post(
            "/api/v1/auth/dev-login",
            json={"email": "blocked@example.com", "name": "Blocked"},
        )
        assert response.status_code == 403
    finally:
        settings.auth_dev_mode = original


def test_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_logout_endpoint(client, auth_login):
    headers, _ = auth_login("logout@example.com")
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200


def test_google_login_failure(client):
    with patch(
        "app.api.auth.verify_google_id_token",
        side_effect=AuthError("Google login failed. Please try again.", status_code=401),
    ):
        response = client.post("/api/v1/auth/google", json={"id_token": "x" * 40})
    assert response.status_code == 401
    assert "google" in response.json()["error"].lower() or "login" in response.json()["error"].lower()


def test_auth_config(client):
    response = client.get("/api/v1/auth/config")
    assert response.status_code == 200
    assert "auth_dev_mode" in response.json()
