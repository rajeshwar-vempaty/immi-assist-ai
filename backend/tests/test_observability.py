"""Observability tests — metrics endpoint."""

from app.observability.metrics import normalize_path


def test_metrics_endpoint(client):
    client.get("/api/v1/health/live")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "llm_requests_total" in response.text


def test_normalize_path_collapses_uuids():
    path = normalize_path("/api/v1/auth/keys/550e8400-e29b-41d4-a716-446655440000")
    assert "550e8400" not in path


def test_normalize_path_truncates_long_paths():
    path = normalize_path("/api/v1/a/b/c/d/e/f/g")
    assert path.endswith("/...")
