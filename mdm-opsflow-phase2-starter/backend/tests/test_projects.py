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


def test_project_creation_documents_can_be_uploaded_to_intake(client: TestClient):
    user = register_user(client, "project-docs@example.com", "Pass12345!", "Project Docs")
    token = user["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Project Docs Civil", "Project Docs First")
    tenant_id = onboarding["tenant_id"]

    create_response = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={
            "project_name": "Document Intake Project",
            "project_number": "DOC-001",
            "customer": "DOT",
            "address": "100 Upload Way",
            "project_manager": "Project Docs",
            "status": "planning",
            "description": "Project with uploaded source documents",
        },
    )
    assert create_response.status_code == 201, create_response.text
    project_id = create_response.json()["id"]

    upload = client.post(
        "/api/intake/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        data={"project_id": project_id},
        files={
            "file": (
                "scale-ticket.txt",
                b"Ticket: HT-1001\nGross: 78440\nTare: 31100\nNet: 47340\nTons: 23.67\n",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["project_id"] == project_id

    placement = client.post(
        "/api/intake/placement/suggest",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"item_ids": [upload.json()["id"]]},
    )
    assert placement.status_code == 200, placement.text
    assert placement.json()["items"][0]["document_intelligence"]["recommended_module"]


def test_platform_super_admin_can_fetch_project_profitability_without_tenant_header(client: TestClient):
    owner = register_user(client, "tenant-owner@example.com", "Pass12345!", "Tenant Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Northwind Contracting", "Northwind HQ")
    tenant_id = onboarding["tenant_id"]

    create_response = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={
            "project_name": "Warehouse Expansion",
            "project_number": "WH-100",
            "customer": "Northwind",
            "address": "1 Industrial Way",
            "project_manager": "Tenant Owner",
            "status": "active",
            "description": "Dock and yard expansion",
        },
    )
    assert create_response.status_code == 201, create_response.text
    project_id = create_response.json()["id"]

    admin_login = client.post(
        "/api/auth/login",
        json={"email": "founder@mdmopsflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200, admin_login.text
    admin_token = admin_login.json()["tokens"]["access_token"]

    profitability_response = client.get(
        f"/api/projects/{project_id}/profitability",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert profitability_response.status_code == 200, profitability_response.text

    costs_response = client.get(
        f"/api/projects/{project_id}/costs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert costs_response.status_code == 200, costs_response.text
    assert costs_response.json()["total_tickets"] == 0
