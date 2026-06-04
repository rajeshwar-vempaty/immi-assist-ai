"""Checklist API tests with mocked service."""

from unittest.mock import AsyncMock, patch

from app.schemas.schemas import ChecklistCategory, ChecklistItem, ChecklistResponse


@patch("app.api.checklist.ChecklistService")
def test_checklist_endpoint(MockService, client):
    mock_instance = MockService.return_value
    mock_instance.generate = AsyncMock(
        return_value=ChecklistResponse(
            visa_type="H1B",
            form_number="I-129",
            checklist=[
                ChecklistCategory(
                    category="Required",
                    items=[
                        ChecklistItem(
                            document="Form I-129",
                            required=True,
                            description="Petition form",
                        )
                    ],
                )
            ],
            filing_fee="$460",
            estimated_prep_time="2 weeks",
            common_mistakes=["Missing LCA"],
            disclaimer="Informational only.",
        )
    )

    response = client.post(
        "/api/v1/checklist",
        json={"visa_type": "H1B", "details": "New employer transfer"},
        headers={"X-Session-ID": "test-checklist-session"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["visa_type"] == "H1B"
    assert len(data["checklist"]) >= 1
