"""Auth, conversation isolation, encrypted credentials, and logout cleanup tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import get_settings
from app.core.security import decrypt_secret, mask_api_key
from app.models.models import Message, UserProviderCredential


def test_protected_routes_require_auth(client):
    assert client.get("/api/v1/conversations").status_code == 401
    assert client.post("/api/v1/chat", json={"message": "hi"}).status_code == 401
    assert client.get("/api/v1/settings/credentials").status_code == 401


def test_dev_login_and_me(client, auth_login):
    headers, user = auth_login("alice@example.com", "Alice")
    assert user["email"] == "alice@example.com"
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_google_login_mocked(client):
    claims = {
        "sub": "google-sub-123",
        "email": "googleuser@example.com",
        "name": "Google User",
        "picture": "https://example.com/a.png",
    }
    with patch("app.api.auth.verify_google_id_token", return_value=claims):
        resp = client.post("/api/v1/auth/google", json={"id_token": "x" * 40})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["email"] == "googleuser@example.com"
    assert body["access_token"]
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["name"] == "Google User"


def test_conversation_isolation_account_switch(client, auth_login, db_session):
    alice_headers, _ = auth_login("alice@example.com", "Alice")
    bob_headers, _ = auth_login("bob@example.com", "Bob")

    created = client.post(
        "/api/v1/conversations",
        headers=alice_headers,
        json={"title": "Alice secret chat"},
    )
    assert created.status_code == 200
    conv_id = created.json()["id"]

    db_session.add(
        Message(
            conversation_id=conv_id,
            role="user",
            content="Alice private question",
        )
    )
    db_session.commit()

    alice_list = client.get("/api/v1/conversations", headers=alice_headers)
    assert alice_list.status_code == 200
    assert len(alice_list.json()["conversations"]) == 1
    assert alice_list.json()["conversations"][0]["title"] == "Alice secret chat"

    bob_list = client.get("/api/v1/conversations", headers=bob_headers)
    assert bob_list.status_code == 200
    assert bob_list.json()["conversations"] == []

    bob_get = client.get(f"/api/v1/conversations/{conv_id}", headers=bob_headers)
    assert bob_get.status_code == 404

    # Alice signs back in on a "new session" and still sees her history
    alice2_headers, _ = auth_login("alice@example.com", "Alice")
    again = client.get("/api/v1/conversations", headers=alice2_headers)
    assert len(again.json()["conversations"]) == 1
    detail = client.get(f"/api/v1/conversations/{conv_id}", headers=alice2_headers)
    assert detail.status_code == 200
    assert any(m["content"] == "Alice private question" for m in detail.json()["messages"])


def test_credentials_encrypted_and_masked(client, auth_login, db_session):
    headers, _ = auth_login("keys@example.com", "Keys")
    raw_key = "sk-test-secret-key-abcdef123456"

    with patch("app.services.credentials_service.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.validate_key = AsyncMock(return_value=True)
        mock_get.return_value = mock_provider
        saved = client.put(
            "/api/v1/settings/credentials/openai",
            headers=headers,
            json={"api_key": raw_key},
        )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["configured"] is True
    assert body["masked_key"] == mask_api_key(raw_key)
    assert raw_key not in saved.text
    assert "sk-test-secret" not in body["masked_key"]

    listed = client.get("/api/v1/settings/credentials", headers=headers)
    assert listed.status_code == 200
    assert raw_key not in listed.text
    creds = listed.json()["credentials"]
    assert len(creds) == 1
    assert creds[0]["masked_key"] == mask_api_key(raw_key)

    row = db_session.query(UserProviderCredential).one()
    assert row.encrypted_api_key != raw_key
    assert decrypt_secret(row.encrypted_api_key) == raw_key

    other_headers, _ = auth_login("other@example.com", "Other")
    other_creds = client.get("/api/v1/settings/credentials", headers=other_headers)
    assert other_creds.json()["credentials"] == []


def test_unauthorized_credential_delete(client, auth_login):
    a_headers, _ = auth_login("a@ex.com", "A")
    b_headers, _ = auth_login("b@ex.com", "B")
    with patch("app.services.credentials_service.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.validate_key = AsyncMock(return_value=True)
        mock_get.return_value = mock_provider
        client.put(
            "/api/v1/settings/credentials/openai",
            headers=a_headers,
            json={"api_key": "sk-aaaaaaaaaaaaaaaaaaaa"},
        )
    deleted = client.delete(
        "/api/v1/settings/credentials/openai",
        headers=b_headers,
    )
    assert deleted.status_code == 404
    listed = client.get("/api/v1/settings/credentials", headers=a_headers)
    assert len(listed.json()["credentials"]) == 1


def test_chat_missing_api_key_message(client, auth_login):
    headers, _ = auth_login("nokey@example.com", "NoKey")
    resp = client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": "What is I-485?", "provider": "openai", "model": "gpt-4o-mini"},
    )
    assert resp.status_code == 400
    assert "API key" in resp.json()["error"]
    assert "settings" in resp.json()["error"].lower()


def test_logout_clears_cookie_session(client, auth_login):
    headers, _ = auth_login("out@example.com", "Out")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    # Also establish cookie session via login response cookies on client
    out = client.post("/api/v1/auth/logout")
    assert out.status_code == 200
    me_cookie = client.get("/api/v1/auth/me")
    assert me_cookie.status_code == 401


def test_mask_helper():
    assert mask_api_key("sk-abcdefghijklmnop") == "sk-****mnop"
    assert mask_api_key("short") == "****"


def test_auth_config_exposes_flags(client):
    settings = get_settings()
    resp = client.get("/api/v1/auth/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "google_client_id" in data
    assert data["auth_dev_mode"] is settings.auth_dev_mode
