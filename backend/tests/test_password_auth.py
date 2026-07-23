"""Email/password registration and login tests."""

from unittest.mock import patch

from app.core.security import hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("secret-pass-123")
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password("secret-pass-123", hashed)
    assert not verify_password("wrong", hashed)


def test_register_and_login(client):
    with patch("app.services.password_auth.send_welcome_email") as mock_mail:
        mock_mail.return_value = {"sent": False, "mode": "log_only"}
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "username": "Maya",
                "email": "maya@example.com",
                "password": "securepass1",
            },
        )
    assert reg.status_code == 200, reg.text
    body = reg.json()
    assert body["user"]["email"] == "maya@example.com"
    assert body["user"]["name"] == "Maya"
    assert body["access_token"]
    mock_mail.assert_called_once()

    # Duplicate email
    again = client.post(
        "/api/v1/auth/register",
        json={
            "username": "Maya2",
            "email": "maya@example.com",
            "password": "securepass1",
        },
    )
    assert again.status_code == 409

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "maya@example.com", "password": "securepass1"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "maya@example.com"

    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "maya@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401


def test_register_sends_welcome_summary(client):
    with patch("app.services.email_service.logger") as mock_logger:
        # Use real send_welcome_email path with log-only
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "username": "Sam",
                "email": "sam@example.com",
                "password": "securepass1",
            },
        )
    assert reg.status_code == 200
    assert reg.json()["welcome_email"]["mode"] in {"log_only", "smtp", "error"}
