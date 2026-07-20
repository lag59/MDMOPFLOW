from fastapi.testclient import TestClient


def register_user(client: TestClient, email: str, password: str, display_name: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    assert response.status_code == 201
    return response.json()


def complete_onboarding(client: TestClient, token: str, company_name: str, first_project_name: str) -> dict:
    response = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "company_name": company_name,
            "company_type": "General Contractor",
            "language": "en",
            "modules": ["Projects"],
            "invite_emails": [],
            "first_project_name": first_project_name,
        },
    )
    assert response.status_code == 201
    return response.json()
