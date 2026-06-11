"""Schema validation tests."""

import pytest
from pydantic import ValidationError

from app.schemas.schemas import ChatRequest, ChecklistRequest, VisaType


def test_chat_request_valid():
    req = ChatRequest(message="How does H1B work?")
    assert req.message == "How does H1B work?"


def test_chat_request_empty_invalid():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_checklist_request():
    req = ChecklistRequest(visa_type=VisaType.H1B, details="New employer")
    assert req.visa_type == VisaType.H1B
