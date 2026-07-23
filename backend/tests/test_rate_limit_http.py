"""HTTP 429 rate limit integration test."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import get_settings
from app.models.models import User
from app.providers import ChatCompletionResult


@patch("app.services.chat_service.get_rag_service")
@patch("app.services.chat_service.get_provider")
def test_rate_limit_returns_429(mock_get_provider, mock_rag, client, auth_login, db_session):
    headers, user = auth_login("ratelimit@example.com", "Rate")
    # Force free-tier limits for this user
    row = db_session.query(User).filter(User.id == user["id"]).first()
    row.tier = "free"
    db_session.commit()

    with patch("app.services.credentials_service.get_provider") as mock_cred_provider:
        mock_cred = MagicMock()
        mock_cred.validate_key = AsyncMock(return_value=True)
        mock_cred_provider.return_value = mock_cred
        saved = client.put(
            "/api/v1/settings/credentials/openai",
            headers=headers,
            json={"api_key": "sk-test-openai-key-abcdef123456"},
        )
        assert saved.status_code == 200

    mock_rag.return_value.retrieve.return_value = []
    mock_rag.return_value.format_context.return_value = ("context", [])
    adapter = MagicMock()
    adapter.chat = AsyncMock(
        return_value=ChatCompletionResult(
            content="Hello",
            provider="openai",
            model="gpt-4o-mini",
        )
    )
    mock_get_provider.return_value = adapter

    settings = get_settings()
    payload = {
        "message": "Hello",
        "provider": "openai",
        "model": "gpt-4o-mini",
    }

    for _ in range(settings.free_tier_daily_limit):
        response = client.post("/api/v1/chat", headers=headers, json=payload)
        assert response.status_code == 200, response.text

    response = client.post("/api/v1/chat", headers=headers, json={**payload, "message": "One more"})
    assert response.status_code == 429
    assert "limit" in response.json()["error"].lower()
