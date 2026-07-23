"""RFE API tests."""

from unittest.mock import AsyncMock, patch

from app.schemas.schemas import RFEAnalysis


@patch("app.api.rfe.RFEService")
def test_rfe_endpoint(MockService, client, auth_login):
    headers, _ = auth_login("rfe@example.com")
    mock_instance = MockService.return_value
    mock_instance.analyze = AsyncMock(
        return_value=RFEAnalysis(
            summary="USCIS requests additional evidence of specialty occupation.",
            deadline_info="Respond within 87 days.",
            risk_level="moderate",
            points=[{"issue": "Specialty occupation", "evidence_suggestions": ["Job description"]}],
            response_outline=["Cover letter", "Exhibits"],
            next_steps=["Consult attorney"],
            disclaimer="Informational only.",
        )
    )

    response = client.post(
        "/api/v1/rfe/analyze",
        headers=headers,
        json={"rfe_text": "Please provide evidence that the position qualifies as a specialty occupation."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "moderate"
    assert len(data["points"]) == 1
