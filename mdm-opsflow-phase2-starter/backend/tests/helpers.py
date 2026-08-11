from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def register_user(client: TestClient, email: str, password: str, display_name: str) -> dict:
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "is_test": True,
            "created_by_automation": True,
            "test_run_id": "pytest-suite",
            "expires_at": expires_at,
        },
    )
    assert response.status_code == 201
    return response.json()


def complete_onboarding(client: TestClient, token: str, company_name: str, first_project_name: str) -> dict:
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    response = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "company_name": company_name,
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects"],
            "invite_emails": [],
            "first_project_name": first_project_name,
            "tenant_type": "test",
            "is_test": True,
            "created_by_automation": True,
            "test_run_id": "pytest-suite",
            "expires_at": expires_at,
        },
    )
    assert response.status_code == 201
    return response.json()
