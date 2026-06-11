"""HTTP 429 rate limit integration test."""

from unittest.mock import AsyncMock, patch

from app.core.config import get_settings
from app.core.llm_router import ClassifiedIntent, Intent, LLMResponse


@patch("app.services.chat_service.get_rag_service")
@patch("app.services.chat_service.get_llm_router")
def test_rate_limit_returns_429(mock_router, mock_rag, client):
    mock_rag.return_value.retrieve.return_value = []
    mock_rag.return_value.format_context.return_value = ("context", [])

    mock_router.return_value.classify_intent = AsyncMock(
        return_value=ClassifiedIntent(intent=Intent.GENERAL, confidence=0.9, sub_topic="hi")
    )
    mock_router.return_value.route_and_respond = AsyncMock(
        return_value=LLMResponse(
            content="Hello",
            model_used="test",
            intent=Intent.GENERAL,
            confidence=0.9,
            sources=[],
        )
    )

    settings = get_settings()
    session_id = "rate-limit-http-session"

    for _ in range(settings.free_tier_daily_limit):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
            headers={"X-Session-ID": session_id},
        )
        assert response.status_code == 200

    response = client.post(
        "/api/v1/chat",
        json={"message": "One more"},
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 429
    assert "limit" in response.json()["error"].lower()
