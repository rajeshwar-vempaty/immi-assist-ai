"""Chat API tests with mocked provider adapters and auth."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.providers import ChatCompletionResult


def _seed_openai_key(client, headers):
    with patch("app.services.credentials_service.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.validate_key = AsyncMock(return_value=True)
        mock_get.return_value = mock_provider
        resp = client.put(
            "/api/v1/settings/credentials/openai",
            headers=headers,
            json={"api_key": "sk-test-openai-key-abcdef123456"},
        )
    assert resp.status_code == 200, resp.text


@patch("app.services.chat_service.get_rag_service")
@patch("app.services.chat_service.get_provider")
def test_chat_endpoint(mock_get_provider, mock_rag, client, auth_login):
    headers, _ = auth_login("chat@example.com", "Chat User")
    _seed_openai_key(client, headers)

    mock_rag.return_value.retrieve.return_value = []
    mock_rag.return_value.format_context.return_value = ("context", [])

    adapter = MagicMock()
    adapter.chat = AsyncMock(
        return_value=ChatCompletionResult(
            content="H-1B is a specialty occupation visa.",
            provider="openai",
            model="gpt-4o-mini",
        )
    )
    mock_get_provider.return_value = adapter

    response = client.post(
        "/api/v1/chat",
        headers=headers,
        json={
            "message": "What is H1B?",
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "response" in data
    assert data["intent"] == "POLICY_QA"
    assert data["provider"] == "openai"
    assert data["conversation_id"]


@patch("app.services.chat_service.get_rag_service")
@patch("app.services.chat_service.get_provider")
def test_chat_timeline_uses_form_number_instead_of_visa_label(
    mock_get_provider, mock_rag, client, auth_login
):
    headers, _ = auth_login("timeline-chat@example.com", "Timeline")
    _seed_openai_key(client, headers)

    mock_rag.return_value.retrieve.return_value = []
    mock_rag.return_value.format_context.return_value = ("processing context", [])

    adapter = MagicMock()
    adapter.chat = AsyncMock(
        return_value=ChatCompletionResult(
            content="Timeline response",
            provider="openai",
            model="gpt-4o-mini",
        )
    )
    mock_get_provider.return_value = adapter

    response = client.post(
        "/api/v1/chat",
        headers=headers,
        json={
            "message": "How long does H1B I-129 processing take?",
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
    )

    assert response.status_code == 200, response.text
    system_prompt = adapter.chat.call_args.kwargs["system_prompt"]
    assert "- Petition/Form Type: I-129" in system_prompt
    assert "- Petition/Form Type: H1B" not in system_prompt
    assert "- Category: H1B" in system_prompt
