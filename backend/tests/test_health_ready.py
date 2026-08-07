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
@patch("app.api.health._knowledge_base_mode", return_value="expanded")
def test_readiness_rejects_expanded_when_require_scraped(mock_mode, mock_rag, mock_settings, client):
    """expanded (!= scraped) must not satisfy REQUIRE_SCRAPED_KB."""
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
    assert response.status_code == 503
    assert response.json()["scraped_kb_ok"] is False


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
    mock_service.policy_collection.count.return_value = 15  # capped scrape can be <20
    mock_service.timeline_collection.count.return_value = 8
    mock_rag.return_value = mock_service

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["knowledge_base_mode"] == "scraped"
    assert data["scraped_kb_ok"] is True


@patch("app.api.health.get_settings")
@patch("app.api.health.get_rag_service")
@patch("app.api.health._knowledge_base_mode", return_value="sample")
def test_production_env_alone_does_not_block_sample_bootstrap(
    mock_mode, mock_rag, mock_settings, client
):
    """APP_ENV=production must not imply require_scraped (scheduler bootstrap)."""
    settings = MagicMock()
    settings.min_knowledge_base_documents = 10
    settings.require_scraped_kb = False
    settings.app_env = "production"
    settings.resolved_chroma_dir = "/tmp/chroma"
    mock_settings.return_value = settings

    mock_service = MagicMock()
    mock_service.policy_collection.count.return_value = 12
    mock_service.timeline_collection.count.return_value = 8
    mock_rag.return_value = mock_service

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["require_scraped_kb"] is False


@patch("app.api.health.get_settings")
def test_knowledge_base_mode_scraped_even_when_small_count(mock_settings, tmp_path):
    from app.api import health as health_mod

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "corpus_manifest.json").write_text(
        '{"corpus_origin":"scraped","document_count":8}', encoding="utf-8"
    )
    settings = MagicMock()
    settings.resolved_chroma_dir = str(tmp_path / "chroma_db")
    mock_settings.return_value = settings

    assert health_mod._knowledge_base_mode(8) == "scraped"
