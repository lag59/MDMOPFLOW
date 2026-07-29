from fastapi.testclient import TestClient


def test_vendor_portal_records_are_created_and_listed_for_vendor_member(client: TestClient) -> None:
    owner_register_response = client.post(
        "/api/auth/register",
        json={"email": "vendor.owner@example.com", "password": "Pass12345!", "display_name": "Vendor Owner"},
    )
    assert owner_register_response.status_code == 201, owner_register_response.text
    owner_token = owner_register_response.json()["tokens"]["access_token"]

    vendor_register_response = client.post(
        "/api/auth/register",
        json={"email": "vendor.member@example.com", "password": "Pass12345!", "display_name": "Vendor Member"},
    )
    assert vendor_register_response.status_code == 201, vendor_register_response.text
    vendor_token = vendor_register_response.json()["tokens"]["access_token"]

    onboarding_response = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "company_name": "Vendor Co",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects", "Documents"],
            "invite_emails": [],
            "first_project_name": "Vendor Project",
        },
    )
    assert onboarding_response.status_code == 201, onboarding_response.text
    tenant_id = onboarding_response.json()["tenant_id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id}

    assign_response = client.post(
        "/api/tenant-users",
        headers=owner_headers,
        json={"email": "vendor.member@example.com", "role_name": "vendor"},
    )
    assert assign_response.status_code == 201, assign_response.text

    vendor_headers = {"Authorization": f"Bearer {vendor_token}", "X-Tenant-ID": tenant_id}
    project_response = client.get("/api/projects", headers=vendor_headers)
    assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()[0]["id"]

    po_response = client.post(
        "/api/vendor/purchase-orders",
        headers=vendor_headers,
        json={
            "project_id": project_id,
            "po_number": "PO-1001",
            "vendor_name": "Acme Materials",
            "description": "Aggregate delivery",
            "status": "open",
            "total_amount": "12500.00",
        },
    )
    assert po_response.status_code == 201, po_response.text
    purchase_order_id = po_response.json()["id"]

    invoice_response = client.post(
        "/api/vendor/invoice-submissions",
        headers=vendor_headers,
        json={
            "project_id": project_id,
            "purchase_order_id": purchase_order_id,
            "invoice_number": "INV-501",
            "vendor_name": "Acme Materials",
            "amount": "6400.00",
            "status": "submitted",
            "notes": "First half of delivered loads",
        },
    )
    assert invoice_response.status_code == 201, invoice_response.text

    delivery_response = client.post(
        "/api/vendor/delivery-records",
        headers=vendor_headers,
        json={
            "project_id": project_id,
            "purchase_order_id": purchase_order_id,
            "ticket_number": "TCK-DEL-01",
            "vendor_name": "Acme Materials",
            "destination": "North Yard",
            "status": "delivered",
            "received_at": "2026-07-28T10:00:00Z",
        },
    )
    assert delivery_response.status_code == 201, delivery_response.text

    compliance_response = client.post(
        "/api/vendor/compliance-documents",
        headers=vendor_headers,
        json={
            "project_id": project_id,
            "document_name": "Insurance Certificate",
            "vendor_name": "Acme Materials",
            "status": "current",
            "expires_at": "2026-12-31T00:00:00Z",
            "notes": "Annual renewal on file",
        },
    )
    assert compliance_response.status_code == 201, compliance_response.text

    purchase_orders_list = client.get("/api/vendor/purchase-orders", headers=vendor_headers)
    assert purchase_orders_list.status_code == 200, purchase_orders_list.text
    assert purchase_orders_list.json()[0]["po_number"] == "PO-1001"

    invoice_submissions_list = client.get("/api/vendor/invoice-submissions", headers=vendor_headers)
    assert invoice_submissions_list.status_code == 200, invoice_submissions_list.text
    assert invoice_submissions_list.json()[0]["invoice_number"] == "INV-501"

    delivery_records_list = client.get("/api/vendor/delivery-records", headers=vendor_headers)
    assert delivery_records_list.status_code == 200, delivery_records_list.text
    assert delivery_records_list.json()[0]["ticket_number"] == "TCK-DEL-01"

    compliance_documents_list = client.get("/api/vendor/compliance-documents", headers=vendor_headers)
    assert compliance_documents_list.status_code == 200, compliance_documents_list.text
    assert compliance_documents_list.json()[0]["document_name"] == "Insurance Certificate"
