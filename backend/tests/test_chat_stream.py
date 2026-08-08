"""Chat streaming endpoint tests."""

from unittest.mock import AsyncMock, patch

from app.schemas.schemas import ChatResponse


@patch("app.api.chat.ChatService")
def test_chat_stream_sse(MockService, client, auth_login):
    headers, _ = auth_login("stream@example.com")

    async def fake_stream(_request):
        yield {"type": "start", "conversation_id": "c1", "intent": "POLICY_QA", "provider": "openai", "model": "gpt-4o-mini"}
        yield {"type": "token", "text": "Hello "}
        yield {"type": "token", "text": "world"}
        yield {
            "type": "done",
            "response": "Hello world",
            "intent": "POLICY_QA",
            "confidence": 0.7,
            "model_used": "gpt-4o-mini",
            "provider": "openai",
            "sources": [],
            "requires_lawyer": False,
            "conversation_id": "c1",
        }

    mock_instance = MockService.return_value
    mock_instance.stream = fake_stream

    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        headers=headers,
        json={"message": "What is H-1B?", "provider": "openai", "model": "gpt-4o-mini"},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = "".join(response.iter_text())
        assert "Hello" in body
        assert '"type": "done"' in body or '"type":"done"' in body


@patch("app.api.chat.ChatService")
def test_chat_json_still_works(MockService, client, auth_login):
    headers, _ = auth_login("chatjson@example.com")
    mock_instance = MockService.return_value
    mock_instance.process = AsyncMock(
        return_value=ChatResponse(
            response="Answer",
            intent="POLICY_QA",
            confidence=0.8,
            model_used="gpt-4o-mini",
            provider="openai",
            sources=[],
            conversation_id="c2",
            session_id="c2",
        )
    )
    response = client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": "Hello", "provider": "openai", "model": "gpt-4o-mini"},
    )
    assert response.status_code == 200
    assert response.json()["response"] == "Answer"
