"""USCIS processing-times endpoints — snapshot fallback behavior."""

from unittest.mock import AsyncMock, patch


def _auth(client, auth_login):
    headers, _ = auth_login("uscis-times@example.com", "Times User")
    return headers


@patch("app.services.uscis_times_service._fetch_live", new_callable=AsyncMock, return_value=None)
def test_forms_fall_back_to_snapshot(mock_live, client, auth_login):
    headers = _auth(client, auth_login)
    resp = client.get("/api/v1/timeline/uscis/forms", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "snapshot"
    ids = [f["id"] for f in data["forms"]]
    assert "I-129" in ids and "N-400" in ids


@patch("app.services.uscis_times_service._fetch_live", new_callable=AsyncMock, return_value=None)
def test_cascading_lookups_and_processing_time(mock_live, client, auth_login):
    headers = _auth(client, auth_login)

    cats = client.get("/api/v1/timeline/uscis/categories?form=I-129", headers=headers).json()
    assert cats["source"] == "snapshot"
    cat_ids = [c["id"] for c in cats["categories"]]
    assert "e-treaty" in cat_ids

    offices = client.get(
        "/api/v1/timeline/uscis/offices?form=I-129&category=e-treaty", headers=headers
    ).json()
    assert offices["offices"][0]["id"] == "scops"

    pt = client.get(
        "/api/v1/timeline/uscis/processing-time?form=I-129&category=e-treaty&office=scops",
        headers=headers,
    ).json()
    assert pt["source"] == "snapshot"
    assert pt["months"] == 18.5
    assert pt["uscis_url"].startswith("https://egov.uscis.gov")


@patch("app.services.uscis_times_service._fetch_live", new_callable=AsyncMock)
def test_live_payload_normalization(mock_live, client, auth_login):
    headers = _auth(client, auth_login)
    mock_live.return_value = {
        "data": {
            "processing_time": {
                "form_name": "I-129",
                "subtypes": [
                    {
                        "publication_date": "June 30, 2026",
                        "range": [
                            {"unit": "Months", "value": 2.0},
                            {"unit": "Months", "value": 18.5},
                        ],
                    }
                ],
            }
        }
    }
    pt = client.get(
        "/api/v1/timeline/uscis/processing-time?form=I-129&category=e-treaty&office=scops",
        headers=headers,
    ).json()
    assert pt["source"] == "live"
    assert pt["months"] == 18.5
    assert pt["publication_date"] == "June 30, 2026"


def test_uscis_endpoints_require_auth(client):
    assert client.get("/api/v1/timeline/uscis/forms").status_code == 401
