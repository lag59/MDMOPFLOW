from fastapi.testclient import TestClient


def test_end_to_end_module_role_flows(client: TestClient) -> None:
    owner_register = client.post(
        "/api/auth/register",
        json={"email": "flow.owner@example.com", "password": "Pass12345!", "display_name": "Flow Owner"},
    )
    assert owner_register.status_code == 201, owner_register.text
    owner_token = owner_register.json()["tokens"]["access_token"]

    estimator_register = client.post(
        "/api/auth/register",
        json={"email": "flow.estimator@example.com", "password": "Pass12345!", "display_name": "Flow Estimator"},
    )
    assert estimator_register.status_code == 201, estimator_register.text
    estimator_token = estimator_register.json()["tokens"]["access_token"]

    payroll_register = client.post(
        "/api/auth/register",
        json={"email": "flow.payroll@example.com", "password": "Pass12345!", "display_name": "Flow Payroll"},
    )
    assert payroll_register.status_code == 201, payroll_register.text
    payroll_token = payroll_register.json()["tokens"]["access_token"]

    vendor_register = client.post(
        "/api/auth/register",
        json={"email": "flow.vendor@example.com", "password": "Pass12345!", "display_name": "Flow Vendor"},
    )
    assert vendor_register.status_code == 201, vendor_register.text
    vendor_token = vendor_register.json()["tokens"]["access_token"]

    customer_register = client.post(
        "/api/auth/register",
        json={"email": "flow.customer@example.com", "password": "Pass12345!", "display_name": "Flow Customer"},
    )
    assert customer_register.status_code == 201, customer_register.text
    customer_token = customer_register.json()["tokens"]["access_token"]

    onboarding = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "company_name": "Flow Co",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects", "Payroll", "Documents"],
            "invite_emails": [],
            "first_project_name": "Flow Project",
        },
    )
    assert onboarding.status_code == 201, onboarding.text
    tenant_id = onboarding.json()["tenant_id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id}

    for email, role_name in [
        ("flow.estimator@example.com", "estimator"),
        ("flow.payroll@example.com", "payroll"),
        ("flow.vendor@example.com", "vendor"),
        ("flow.customer@example.com", "customer"),
    ]:
        response = client.post(
            "/api/tenant-users",
            headers=owner_headers,
            json={"email": email, "role_name": role_name},
        )
        assert response.status_code == 201, response.text

    estimator_headers = {"Authorization": f"Bearer {estimator_token}", "X-Tenant-ID": tenant_id}
    payroll_headers = {"Authorization": f"Bearer {payroll_token}", "X-Tenant-ID": tenant_id}
    vendor_headers = {"Authorization": f"Bearer {vendor_token}", "X-Tenant-ID": tenant_id}
    customer_headers = {"Authorization": f"Bearer {customer_token}", "X-Tenant-ID": tenant_id}

    projects_response = client.get("/api/projects", headers=owner_headers)
    assert projects_response.status_code == 200, projects_response.text
    project_id = projects_response.json()[0]["id"]

    employee_response = client.post(
        "/api/employees",
        headers=owner_headers,
        json={
            "name": "Dana Cruz",
            "role_title": "Operator",
            "email": "dana@example.com",
            "phone": "555-0102",
            "department": "Field",
            "status": "active",
        },
    )
    assert employee_response.status_code == 201, employee_response.text
    employee_id = employee_response.json()["id"]

    estimator_create = client.post(
        "/api/estimator/takeoffs",
        headers=estimator_headers,
        json={
            "project_id": project_id,
            "takeoff_number": "FLOW-TK-01",
            "material_name": "Base Rock",
            "quantity": "25.00",
            "unit_of_measure": "cy",
            "estimated_cost": "3500.00",
            "status": "draft",
            "notes": "Flow test",
        },
    )
    assert estimator_create.status_code == 201, estimator_create.text

    payroll_create = client.post(
        "/api/payroll/timecards",
        headers=payroll_headers,
        json={
            "employee_id": employee_id,
            "project_id": project_id,
            "work_date": "2026-07-28T00:00:00Z",
            "regular_hours": "8.00",
            "overtime_hours": "1.00",
            "double_time_hours": "0.00",
            "cost_code": "FLOW-100",
            "work_description": "Flow test labor",
            "status": "submitted",
        },
    )
    assert payroll_create.status_code == 201, payroll_create.text

    vendor_create = client.post(
        "/api/vendor/purchase-orders",
        headers=vendor_headers,
        json={
            "project_id": project_id,
            "po_number": "FLOW-PO-01",
            "vendor_name": "Flow Supply",
            "description": "Flow test procurement",
            "status": "open",
            "total_amount": "900.00",
        },
    )
    assert vendor_create.status_code == 201, vendor_create.text

    customer_projects = client.get("/api/customer-portal/projects", headers=customer_headers)
    assert customer_projects.status_code == 200, customer_projects.text
    assert len(customer_projects.json()) == 1

    # Cross-domain enforcement checks
    vendor_cannot_write_payroll = client.post(
        "/api/payroll/timecards",
        headers=vendor_headers,
        json={
            "employee_id": employee_id,
            "project_id": project_id,
            "work_date": "2026-07-29T00:00:00Z",
            "regular_hours": "1.00",
            "overtime_hours": "0.00",
            "double_time_hours": "0.00",
            "cost_code": "FLOW-200",
            "work_description": "Should fail",
            "status": "draft",
        },
    )
    assert vendor_cannot_write_payroll.status_code == 403, vendor_cannot_write_payroll.text

    customer_cannot_write_estimator = client.post(
        "/api/estimator/takeoffs",
        headers=customer_headers,
        json={
            "project_id": project_id,
            "takeoff_number": "FLOW-TK-FAIL",
            "material_name": "Should Fail",
            "quantity": "1.00",
            "unit_of_measure": "cy",
            "status": "draft",
            "notes": "Forbidden",
        },
    )
    assert customer_cannot_write_estimator.status_code == 403, customer_cannot_write_estimator.text
