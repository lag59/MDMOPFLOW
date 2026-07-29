from fastapi.testclient import TestClient


def test_customer_portal_returns_safe_project_billing_and_document_views(client: TestClient) -> None:
    owner_register_response = client.post(
        "/api/auth/register",
        json={"email": "customer.owner@example.com", "password": "Pass12345!", "display_name": "Customer Owner"},
    )
    assert owner_register_response.status_code == 201, owner_register_response.text
    owner_token = owner_register_response.json()["tokens"]["access_token"]

    customer_register_response = client.post(
        "/api/auth/register",
        json={"email": "customer.member@example.com", "password": "Pass12345!", "display_name": "Customer Member"},
    )
    assert customer_register_response.status_code == 201, customer_register_response.text
    customer_token = customer_register_response.json()["tokens"]["access_token"]

    onboarding_response = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "company_name": "Customer Co",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects", "Documents"],
            "invite_emails": [],
            "first_project_name": "Customer Portal Project",
        },
    )
    assert onboarding_response.status_code == 201, onboarding_response.text
    tenant_id = onboarding_response.json()["tenant_id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id}

    assign_response = client.post(
        "/api/tenant-users",
        headers=owner_headers,
        json={"email": "customer.member@example.com", "role_name": "customer"},
    )
    assert assign_response.status_code == 201, assign_response.text

    customer_headers = {"Authorization": f"Bearer {customer_token}", "X-Tenant-ID": tenant_id}

    project_response = client.get("/api/projects", headers=owner_headers)
    assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()[0]["id"]

    ticket_response = client.post(
        "/api/tickets",
        headers=owner_headers,
        json={
            "project_id": project_id,
            "ticket_number": "TCK-CUST-01",
            "truck": "TRK-1",
            "driver": "Alex",
            "material": "Aggregate",
            "origin": "Pit A",
            "destination": "Customer Portal Project",
            "tons": "10.00",
            "volume_yards": "8.00",
            "fuel_cost": "100.00",
            "revenue": "1500.00",
            "status": "approved",
        },
    )
    assert ticket_response.status_code == 201, ticket_response.text

    intake_response = client.post(
        "/api/intake/upload",
        headers=owner_headers,
        files={"file": ("portal.txt", b"portal document", "text/plain")},
    )
    assert intake_response.status_code == 201, intake_response.text

    projects_response = client.get("/api/customer-portal/projects", headers=customer_headers)
    assert projects_response.status_code == 200, projects_response.text
    project_payload = projects_response.json()[0]
    assert project_payload["project_name"] == "Customer Portal Project"
    assert project_payload["actual_revenue"] == "1500.00"
    assert project_payload["ticket_count"] == 1

    billing_response = client.get(f"/api/customer-portal/projects/{project_id}/billing-status", headers=customer_headers)
    assert billing_response.status_code == 200, billing_response.text
    billing_payload = billing_response.json()
    assert billing_payload["actual_revenue"] == "1500.00"
    assert billing_payload["ticket_count"] == 1
    assert "actual_cost" not in billing_payload

    document_response = client.get(f"/api/customer-portal/projects/{project_id}/documents", headers=customer_headers)
    assert document_response.status_code == 200, document_response.text
    document_payload = document_response.json()
    assert document_payload["project_id"] == project_id
    assert "total_documents" in document_payload
    assert "pending_review_documents" in document_payload
