"""Unit tests for case profile formatting helpers."""

from app.schemas.schemas import CaseProfileResponse
from app.services.case_profile_service import format_profile_context


def test_format_profile_context_includes_key_fields():
    profile = CaseProfileResponse(
        visa_type="H1B",
        form_number="I-129",
        has_dependents=True,
        premium_processing=False,
        employer_name="Acme",
        notes="Transfer",
    )
    text = format_profile_context(profile)
    assert "H1B" in text
    assert "I-129" in text
    assert "Acme" in text
    assert "dependents" in text.lower()


def test_format_profile_context_empty():
    assert "No saved" in format_profile_context(None)
    assert "No saved" in format_profile_context(CaseProfileResponse())
