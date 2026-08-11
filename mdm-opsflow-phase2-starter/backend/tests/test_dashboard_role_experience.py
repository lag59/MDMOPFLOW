from fastapi.testclient import TestClient


def test_dashboard_role_experience_returns_estimator_profile_for_estimator_membership(client: TestClient) -> None:
    owner_register = client.post(
        "/api/auth/register",
        json={"email": "dashboard-owner@example.com", "password": "Pass12345!", "display_name": "Dashboard Owner"},
    )
    assert owner_register.status_code == 201, owner_register.text
    owner_token = owner_register.json()["tokens"]["access_token"]

    estimator_register = client.post(
        "/api/auth/register",
        json={"email": "dashboard-estimator@example.com", "password": "Pass12345!", "display_name": "Dashboard Estimator"},
    )
    assert estimator_register.status_code == 201, estimator_register.text
    estimator_token = estimator_register.json()["tokens"]["access_token"]

    onboarding = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "company_name": "Dashboard Tenant",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects", "Documents"],
            "invite_emails": [],
            "first_project_name": "Dashboard Project",
        },
    )
    assert onboarding.status_code == 201, onboarding.text
    tenant_id = onboarding.json()["tenant_id"]

    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": "dashboard-estimator@example.com", "role_name": "estimator"},
    )
    assert assign.status_code == 201, assign.text

    role_response = client.get(
        "/api/dashboard/role-experience",
        headers={"Authorization": f"Bearer {estimator_token}", "X-Tenant-ID": tenant_id},
    )
    assert role_response.status_code == 200, role_response.text
    payload = role_response.json()

    assert payload["role_key"] == "estimator"
    assert payload["role_label"] == "Estimator"
    assert payload["kpi_order"][0] == "estimates"
    assert any(item["label"] == "Bid Pipeline" for item in payload["modules"])
    assert any(item["label"] == "Open estimator workspace" for item in payload["quick_actions"])


def test_dashboard_role_experience_requires_project_read_permissions(client: TestClient) -> None:
    owner_register = client.post(
        "/api/auth/register",
        json={"email": "dashboard-customer-owner@example.com", "password": "Pass12345!", "display_name": "Dashboard Customer Owner"},
    )
    assert owner_register.status_code == 201, owner_register.text
    owner_token = owner_register.json()["tokens"]["access_token"]

    customer_register = client.post(
        "/api/auth/register",
        json={"email": "dashboard-customer@example.com", "password": "Pass12345!", "display_name": "Dashboard Customer"},
    )
    assert customer_register.status_code == 201, customer_register.text
    customer_token = customer_register.json()["tokens"]["access_token"]

    onboarding = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "company_name": "Dashboard Customer Tenant",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects", "Documents"],
            "invite_emails": [],
            "first_project_name": "Dashboard Customer Project",
        },
    )
    assert onboarding.status_code == 201, onboarding.text
    tenant_id = onboarding.json()["tenant_id"]

    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": "dashboard-customer@example.com", "role_name": "customer"},
    )
    assert assign.status_code == 201, assign.text

    denied = client.get(
        "/api/dashboard/role-experience",
        headers={"Authorization": f"Bearer {customer_token}", "X-Tenant-ID": tenant_id},
    )
    assert denied.status_code == 403
