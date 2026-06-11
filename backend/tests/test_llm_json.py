"""LLM JSON extraction tests."""

import pytest

from app.core.exceptions import LLMResponseError
from app.services.llm_json_service import extract_json


def test_extract_json_plain():
    data = extract_json('{"intent": "POLICY_QA", "confidence": 0.9}')
    assert data["intent"] == "POLICY_QA"


def test_extract_json_fenced():
    text = '```json\n{"form_type": "I-129"}\n```'
    data = extract_json(text)
    assert data["form_type"] == "I-129"


def test_extract_json_invalid():
    with pytest.raises(LLMResponseError):
        extract_json("no json here")
