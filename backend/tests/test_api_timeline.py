"""Timeline API tests."""

from unittest.mock import AsyncMock, patch

from app.schemas.schemas import TimelineResponse


@patch("app.api.timeline.TimelineService")
def test_timeline_endpoint(MockService, client, auth_login):
    headers, _ = auth_login("timeline@example.com")
    mock_instance = MockService.return_value
    mock_instance.estimate = AsyncMock(
        return_value=TimelineResponse(
            form_type="I-129",
            service_center="California Service Center",
            processing_range_months={"min": 2, "max": 4},
            estimated_completion={"earliest": "2026-08", "latest": "2026-10"},
            case_status="NORMAL",
            status_explanation="Within normal range.",
            options_if_delayed=["Submit case inquiry"],
            disclaimer="Estimates only.",
        )
    )

    response = client.post(
        "/api/v1/timeline",
        headers=headers,
        json={"form_type": "I-129", "service_center": "California Service Center"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["form_type"] == "I-129"
    assert data["case_status"] == "NORMAL"
