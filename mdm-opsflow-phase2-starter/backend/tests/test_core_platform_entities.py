from fastapi.testclient import TestClient


def test_core_platform_entities_are_created_and_listed_for_tenant(client: TestClient) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={"email": "core.platform@example.com", "password": "Pass12345!", "display_name": "Core Platform"},
    )
    assert register_response.status_code == 201, register_response.text
    token = register_response.json()["tokens"]["access_token"]

    onboarding_response = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "company_name": "Core Platform Co",
            "company_types": ["General Contractor"],
            "language": "en",
            "modules": ["Projects", "Fleet"],
            "invite_emails": [],
            "first_project_name": "North Yard Buildout",
        },
    )
    assert onboarding_response.status_code == 201, onboarding_response.text
    tenant_id = onboarding_response.json()["tenant_id"]

    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    customer_response = client.post(
        "/api/customers",
        headers=headers,
        json={
            "name": "City of Example",
            "contact_name": "Pat Rivera",
            "email": "pat@example.com",
            "phone": "555-0101",
            "address": "100 Main St",
            "notes": "Primary customer",
        },
    )
    assert customer_response.status_code == 201, customer_response.text

    employee_response = client.post(
        "/api/employees",
        headers=headers,
        json={
            "name": "Jamie Patel",
            "role_title": "Dispatcher",
            "email": "jamie@example.com",
            "phone": "555-0102",
            "department": "Operations",
            "status": "active",
        },
    )
    assert employee_response.status_code == 201, employee_response.text

    equipment_response = client.post(
        "/api/equipment",
        headers=headers,
        json={
            "name": "Excavator 01",
            "equipment_type": "Excavator",
            "capacity_tons": 18.5,
            "status": "available",
            "notes": "Ready for site work",
        },
    )
    assert equipment_response.status_code == 201, equipment_response.text

    truck_response = client.post(
        "/api/trucks",
        headers=headers,
        json={
            "unit_number": "TRK-100",
            "truck_type": "Triaxle",
            "capacity_tons": 22.0,
            "status": "available",
            "assigned_driver": "Jamie Patel",
            "notes": "Primary hauling unit",
        },
    )
    assert truck_response.status_code == 201, truck_response.text

    material_response = client.post(
        "/api/materials",
        headers=headers,
        json={
            "name": "Crusher Run",
            "unit_of_measure": "ton",
            "density_tons_per_cubic_yard": 1.35,
            "description": "Base fill material",
        },
    )
    assert material_response.status_code == 201, material_response.text

    customers_list = client.get("/api/customers", headers=headers)
    assert customers_list.status_code == 200
    assert any(item["name"] == "City of Example" for item in customers_list.json())

    employees_list = client.get("/api/employees", headers=headers)
    assert employees_list.status_code == 200
    assert any(item["name"] == "Jamie Patel" for item in employees_list.json())

    equipment_list = client.get("/api/equipment", headers=headers)
    assert equipment_list.status_code == 200
    assert any(item["name"] == "Excavator 01" for item in equipment_list.json())

    trucks_list = client.get("/api/trucks", headers=headers)
    assert trucks_list.status_code == 200
    assert any(item["unit_number"] == "TRK-100" for item in trucks_list.json())

    materials_list = client.get("/api/materials", headers=headers)
    assert materials_list.status_code == 200
    assert any(item["name"] == "Crusher Run" for item in materials_list.json())
