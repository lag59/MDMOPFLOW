from fastapi.testclient import TestClient

from backend.tests.helpers import complete_onboarding


def test_onboarding_accepts_multiple_company_types_and_modules(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "multi@example.com", "password": "Pass12345!", "display_name": "Multi User"},
    )
    assert response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"email": "multi@example.com", "password": "Pass12345!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["tokens"]["access_token"]

    onboarding_response = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "company_name": "Mixed Operations",
            "company_types": ["Earthwork / Site Development", "Specialty Contractor"],
            "language": "en",
            "modules": ["Projects", "Payroll", "Fleet"],
            "invite_emails": [],
            "first_project_name": "Mixed Project",
        },
    )

    assert onboarding_response.status_code == 201
    body = onboarding_response.json()
    assert body["tenant_id"]
    assert body["project_id"]
