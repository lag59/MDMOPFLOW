from fastapi.testclient import TestClient

from .helpers import complete_onboarding, register_user


def test_project_crud_for_tenant_member(client: TestClient):
    user = register_user(client, "pm@example.com", "Pass12345!", "Project Manager")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Acme Civil", "Acme First")
    tenant_id = onboarding["tenant_id"]

    create_response = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={
            "project_name": "I-95 Expansion",
            "project_number": "I95-001",
            "customer": "DOT",
            "address": "100 Main St",
            "project_manager": "Project Manager",
            "status": "active",
            "description": "Road widening",
        },
    )
    assert create_response.status_code == 201
    project = create_response.json()
    project_id = project["id"]

    get_response = client.get(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert get_response.status_code == 200
    assert get_response.json()["project_name"] == "I-95 Expansion"

    patch_response = client.patch(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"status": "complete", "description": "Delivered"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "complete"

    delete_response = client.delete(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert delete_response.status_code == 204

    get_after_delete = client.get(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert get_after_delete.status_code == 404
