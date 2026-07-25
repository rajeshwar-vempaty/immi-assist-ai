"""Processing-time resolver + timeline grounding tests."""

from unittest.mock import AsyncMock, patch

from app.services.processing_time_resolver import resolve_lookup_keys


def test_resolve_h1b_transfer_message():
    keys = resolve_lookup_keys(message="How long does an H-1B transfer take?")
    assert keys == ("I-129", "h-1b", "scops")


def test_resolve_explicit_form_i765():
    keys = resolve_lookup_keys(message="I-765 OPT processing time")
    assert keys[0] == "I-765"
    assert keys[1] == "c3"


def test_resolve_n400_uses_field_office_default():
    keys = resolve_lookup_keys(form_type="N-400", message="naturalization wait")
    assert keys == ("N-400", "standard", "field-median")


@patch("app.services.timeline_service.generate_structured", new_callable=AsyncMock)
@patch("app.services.timeline_service.lookup_official_time", new_callable=AsyncMock)
@patch("app.services.timeline_service.get_rag_service")
def test_timeline_service_prefers_official_months(mock_rag, mock_lookup, mock_llm, client, auth_login):
    headers, _ = auth_login("pt-ground@example.com", "PT User")

    mock_rag.return_value.retrieve.return_value = []
    mock_rag.return_value.format_context.return_value = ("rag notes", [])
    mock_lookup.return_value = {
        "source": "snapshot",
        "as_of": "2026-06",
        "form": "I-129",
        "category": "h-1b",
        "office": "scops",
        "months": 4.5,
        "uscis_url": "https://egov.uscis.gov/processing-times/",
    }

    class _Raw:
        form_type = "I-129"
        service_center = None
        current_processing_range = {"min_months": 99, "max_months": 99}
        estimated_completion = {}
        case_status = "NORMAL"
        status_explanation = "Should be overridden grounding."
        options_if_delayed = ["Check case status online"]
        disclaimer = "Informational only."

    mock_llm.return_value = _Raw()

    resp = client.post(
        "/api/v1/timeline",
        headers=headers,
        json={"form_type": "I-129", "category": "h-1b"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["official_months"] == 4.5
    assert body["processing_range_months"]["max"] == 4.5
    assert body["data_source"] == "snapshot"
    assert body["data_as_of"] == "2026-06"


@patch("app.services.chat_service.lookup_official_time", new_callable=AsyncMock)
@patch("app.services.chat_service.get_rag_service")
@patch("app.services.chat_service.get_provider")
@patch("app.services.credentials_service.get_provider")
def test_chat_timeline_injects_uscis_banner(
    mock_cred_provider, mock_get_provider, mock_rag, mock_lookup, client, auth_login
):
    from unittest.mock import AsyncMock as AM
    from app.providers import ChatCompletionResult

    headers, _ = auth_login("chat-pt@example.com", "Chat PT")

    mock_cred_provider.return_value.validate_key = AM(return_value=True)
    client.put(
        "/api/v1/settings/credentials/openai",
        headers=headers,
        json={"api_key": "sk-test-openai-key-abcdef123456"},
    )

    mock_rag.return_value.retrieve.return_value = []
    mock_rag.return_value.format_context.return_value = ("context", [])
    mock_lookup.return_value = {
        "source": "snapshot",
        "as_of": "2026-06",
        "form": "I-129",
        "category": "h-1b",
        "office": "scops",
        "months": 4.5,
        "uscis_url": "https://egov.uscis.gov/processing-times/",
    }

    adapter = type("A", (), {})()
    adapter.chat = AM(
        return_value=ChatCompletionResult(
            content="H-1B transfers often take several months depending on the service center.",
            provider="openai",
            model="gpt-4o-mini",
        )
    )
    mock_get_provider.return_value = adapter

    resp = client.post(
        "/api/v1/chat",
        headers=headers,
        json={
            "message": "How long does H-1B transfer processing take?",
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
    )
    assert resp.status_code == 200, resp.text
    text = resp.json()["response"]
    assert "4.5 months" in text
    assert "USCIS published figure" in text
    assert resp.json()["intent"] in ("TIMELINE", "timeline", "Timeline") or "TIMELINE" in resp.json()["intent"].upper()
