"""Readiness health check tests."""

from unittest.mock import MagicMock, patch


@patch("app.api.health.get_rag_service")
def test_readiness_not_ready_low_docs(mock_rag, client):
    mock_service = MagicMock()
    mock_service.policy_collection.count.return_value = 2
    mock_service.timeline_collection.count.return_value = 1
    mock_rag.return_value = mock_service

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
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


@patch("app.api.health.get_settings")
@patch("app.api.health.get_rag_service")
@patch("app.api.health._knowledge_base_mode", return_value="sample")
def test_readiness_rejects_sample_when_require_scraped(mock_mode, mock_rag, mock_settings, client):
    settings = MagicMock()
    settings.min_knowledge_base_documents = 10
    settings.require_scraped_kb = True
    settings.app_env = "development"
    settings.resolved_chroma_dir = "/tmp/chroma"
    mock_settings.return_value = settings

    mock_service = MagicMock()
    mock_service.policy_collection.count.return_value = 12
    mock_service.timeline_collection.count.return_value = 8
    mock_rag.return_value = mock_service

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["knowledge_base_mode"] == "sample"
    assert data["require_scraped_kb"] is True
    assert data["scraped_kb_ok"] is False


@patch("app.api.health.get_settings")
@patch("app.api.health.get_rag_service")
@patch("app.api.health._knowledge_base_mode", return_value="scraped")
def test_readiness_ok_scraped_when_required(mock_mode, mock_rag, mock_settings, client):
    settings = MagicMock()
    settings.min_knowledge_base_documents = 10
    settings.require_scraped_kb = True
    settings.app_env = "production"
    settings.resolved_chroma_dir = "/tmp/chroma"
    mock_settings.return_value = settings

    mock_service = MagicMock()
    mock_service.policy_collection.count.return_value = 120
    mock_service.timeline_collection.count.return_value = 8
    mock_rag.return_value = mock_service

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["knowledge_base_mode"] == "scraped"
    assert data["scraped_kb_ok"] is True
