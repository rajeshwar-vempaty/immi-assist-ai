"""Chat API tests with mocked LLM and RAG."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.core.llm_router import ClassifiedIntent, Intent, LLMResponse


@patch("app.services.chat_service.get_rag_service")
@patch("app.services.chat_service.get_llm_router")
def test_chat_endpoint(mock_router, mock_rag, client):
    mock_rag.return_value.retrieve.return_value = []
    mock_rag.return_value.format_context.return_value = ("context", [])

    mock_router.return_value.classify_intent = AsyncMock(
        return_value=ClassifiedIntent(
            intent=Intent.POLICY_QA,
            confidence=0.9,
            sub_topic="H1B",
        )
    )
    mock_router.return_value.route_and_respond = AsyncMock(
        return_value=LLMResponse(
            content="H-1B is a specialty occupation visa.",
            model_used="test-model",
            intent=Intent.POLICY_QA,
            confidence=0.9,
            sources=[],
        )
    )

    response = client.post(
        "/api/v1/chat",
        json={"message": "What is H1B?"},
        headers={"X-Session-ID": "test-chat-session"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["intent"] == "POLICY_QA"
