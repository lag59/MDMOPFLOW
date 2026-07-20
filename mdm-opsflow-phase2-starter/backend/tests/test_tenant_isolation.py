from fastapi.testclient import TestClient

from .helpers import complete_onboarding, register_user


def test_tenant_isolation_and_super_admin_visibility(client: TestClient):
    a_user = register_user(client, "a@tenant.com", "Pass12345!", "A Admin")
    b_user = register_user(client, "b@tenant.com", "Pass12345!", "B Admin")

    a_token = a_user["tokens"]["access_token"]
    b_token = b_user["tokens"]["access_token"]

    a_onboarding = complete_onboarding(client, a_token, "Company A", "A First Project")
    b_onboarding = complete_onboarding(client, b_token, "Company B", "B First Project")
    a_tenant_id = a_onboarding["tenant_id"]
    b_tenant_id = b_onboarding["tenant_id"]

    a_project = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {a_token}", "X-Tenant-ID": a_tenant_id},
        json={
            "project_name": "A Secret",
            "project_number": "A-001",
            "customer": "A Client",
            "address": "A Address",
            "project_manager": "A PM",
            "status": "active",
            "description": "A data",
        },
    ).json()

    b_project = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {b_token}", "X-Tenant-ID": b_tenant_id},
        json={
            "project_name": "B Secret",
            "project_number": "B-001",
            "customer": "B Client",
            "address": "B Address",
            "project_manager": "B PM",
            "status": "active",
            "description": "B data",
        },
    ).json()

    a_list = client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {a_token}", "X-Tenant-ID": a_tenant_id},
    )
    assert a_list.status_code == 200
    assert not any(item["id"] == b_project["id"] for item in a_list.json())

    b_list = client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {b_token}", "X-Tenant-ID": b_tenant_id},
    )
    assert b_list.status_code == 200
    assert not any(item["id"] == a_project["id"] for item in b_list.json())

    b_cannot_get_a = client.get(
        f"/api/projects/{a_project['id']}",
        headers={"Authorization": f"Bearer {b_token}", "X-Tenant-ID": b_tenant_id},
    )
    assert b_cannot_get_a.status_code == 404

    super_login = client.post(
        "/api/auth/login",
        json={"email": "founder@mdmopsflow.com", "password": "ChangeMe123!"},
    )
    super_token = super_login.json()["tokens"]["access_token"]

    all_projects = client.get("/api/projects", headers={"Authorization": f"Bearer {super_token}"})
    assert all_projects.status_code == 200
    assert any(item["id"] == a_project["id"] for item in all_projects.json())
    assert any(item["id"] == b_project["id"] for item in all_projects.json())

    tenant_b_users = client.get(
        f"/api/admin/tenants/{b_tenant_id}/users",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert tenant_b_users.status_code == 200
    assert all(user["email"] != "a@tenant.com" for user in tenant_b_users.json())

    logs = client.get("/api/admin/audit-logs?limit=100", headers={"Authorization": f"Bearer {super_token}"})
    assert logs.status_code == 200
    actions = [entry["action"] for entry in logs.json()]
    assert "create_project" in actions
    assert "complete_onboarding" in actions


def test_permissions_preview_endpoint_for_super_admin(client: TestClient):
    user = register_user(client, "preview@tenant.com", "Pass12345!", "Preview User")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Preview Co", "Preview Project")

    super_login = client.post(
        "/api/auth/login",
        json={"email": "founder@mdmopsflow.com", "password": "ChangeMe123!"},
    )
    assert super_login.status_code == 200
    super_token = super_login.json()["tokens"]["access_token"]

    preview = client.get(
        f"/api/admin/permissions-preview?user_id={user['user_id']}&tenant_id={onboarding['tenant_id']}",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert preview.status_code == 200
    items = preview.json()["items"]
    assert len(items) >= 1

    first = items[0]
    assert first["user_id"] == user["user_id"]
    assert first["tenant_id"] == onboarding["tenant_id"]
    assert first["role_name"] == "owner"
    assert "project_read" in first["permissions"]
