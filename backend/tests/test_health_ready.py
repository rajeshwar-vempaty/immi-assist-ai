"""Readiness health check tests."""

from unittest.mock import MagicMock, patch


@patch("app.api.health.get_rag_service")
def test_readiness_not_ready_low_docs(mock_rag, client):
    mock_service = MagicMock()
    mock_service.policy_collection.count.return_value = 2
    mock_service.timeline_collection.count.return_value = 1
    mock_rag.return_value = mock_service

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["knowledge_base_documents"] == 2


@patch("app.api.health.get_rag_service")
def test_readiness_ready(mock_rag, client):
    mock_service = MagicMock()
    mock_service.policy_collection.count.return_value = 12
    mock_service.timeline_collection.count.return_value = 8
    mock_rag.return_value = mock_service

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
