"""Case profile API tests."""


def test_case_profile_get_empty(client, auth_login):
    headers, _ = auth_login("profile@example.com")
    response = client.get("/api/v1/case-profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["visa_type"] is None
    assert data["has_dependents"] is False


def test_case_profile_upsert_and_reuse(client, auth_login):
    headers, _ = auth_login("profile2@example.com")
    put = client.put(
        "/api/v1/case-profile",
        headers=headers,
        json={
            "visa_type": "H1B",
            "form_number": "I-129",
            "service_center": "California Service Center",
            "priority_date": "2024-01-15",
            "has_dependents": True,
            "premium_processing": True,
            "employer_name": "Acme Corp",
            "notes": "Transfer pending",
        },
    )
    assert put.status_code == 200
    body = put.json()
    assert body["visa_type"] == "H1B"
    assert body["form_number"] == "I-129"
    assert body["has_dependents"] is True
    assert body["employer_name"] == "Acme Corp"

    got = client.get("/api/v1/case-profile", headers=headers)
    assert got.status_code == 200
    assert got.json()["priority_date"] == "2024-01-15"
    assert got.json()["notes"] == "Transfer pending"


def test_case_profile_requires_auth(client):
    response = client.get("/api/v1/case-profile")
    assert response.status_code in (401, 403)
