from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import Customer, DailyFieldReport, Material, MembershipStatus, Role, TenantMembership
from app.rbac import permissions_csv_for_role
from tests.helpers import complete_onboarding, register_user


def test_ai_routing_endpoint_creates_customer_material_and_report(client: TestClient):
    login_response = client.post(
        "/api/auth/login",
        json={"email": "founder@mdmopsflow.com", "password": "ChangeMe123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["tokens"]["access_token"]

    tenant_id = "tenant-1"
    with SessionLocal() as db:
        from app.models import Tenant

        tenant = db.query(Tenant).filter(Tenant.name == "Acme Civil").first()
        if tenant is None:
            tenant = Tenant(name="Acme Civil", company_type="contractor", preferred_language="en")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        tenant_id = tenant.id

    project_response = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"project_name": "Northwind Site", "project_number": "NW-001"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    response = client.post(
        "/api/ai/workflow/route",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={
            "note": "Company: Northwind Civil\nSupervisor: Avery Chen\nMaterial: Concrete Mix\nWork: Completed excavation\nPlan: Pour foundation",
            "project_id": project_id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["routed"] is True
    assert body["processing_outcome"] == "created"
    assert body["created_count"] == 3
    assert body["customer_created"] is True
    assert body["material_created"] is True
    assert body["report_created"] is True

    with SessionLocal() as db:
        customer = db.query(Customer).filter(Customer.tenant_id == tenant_id, Customer.name == "Northwind Civil").first()
        material = db.query(Material).filter(Material.tenant_id == tenant_id, Material.name == "Concrete Mix").first()
        report = db.query(DailyFieldReport).filter(DailyFieldReport.tenant_id == tenant_id, DailyFieldReport.company_name == "Northwind Civil").first()

    assert customer is not None
    assert material is not None
    assert report is not None


def test_ai_routing_endpoint_accepts_any_active_tenant_member(client: TestClient):
    registered = register_user(client, "vendor-ai-route@example.com", "Pass12345!", "Vendor AI")
    token = registered["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Vendor AI Civil", "Vendor AI First Project")
    tenant_id = onboarding["tenant_id"]
    user_id = registered["user_id"]

    with SessionLocal() as db:
        role = Role(
            tenant_id=tenant_id,
            name="vendor",
            permissions=permissions_csv_for_role("vendor"),
            created_by=user_id,
        )
        db.add(role)
        db.flush()
        memberships = db.query(TenantMembership).filter(TenantMembership.user_id == user_id).all()
        for membership in memberships:
            membership.status = MembershipStatus.INACTIVE
        db.add(
            TenantMembership(
                tenant_id=tenant_id,
                user_id=user_id,
                role_id=role.id,
                status=MembershipStatus.ACTIVE,
                created_by=user_id,
            )
        )
        db.commit()

    response = client.post(
        "/api/ai/workflow/route",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"note": "Material: 57 stone"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["routed"] is True
    assert body["processing_outcome"] == "created"
    assert body["material_created"] is True
    assert body["material_name"] == "57 stone"


def test_ai_routing_extracts_unstructured_field_note(client: TestClient):
    registered = register_user(client, "field-note-ai@example.com", "Pass12345!", "Field Note AI")
    token = registered["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Field Note Civil", "Field Note First Project")
    tenant_id = onboarding["tenant_id"]

    response = client.post(
        "/api/ai/workflow/route",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={
            "note": "Summit Peak Builders completed excavation and placed 57 stone at the east entrance today. Foreman Maria Reyes."
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["routed"] is True
    assert body["processing_outcome"] == "created"
    assert body["customer_created"] is True
    assert body["material_created"] is True
    assert body["report_created"] is True
    assert body["customer_name"] == "Summit Peak Builders"
    assert body["material_name"].lower() == "57 stone"


def test_ai_routing_extracts_bid_contract_style_labels(client: TestClient):
    registered = register_user(client, "contract-note-ai@example.com", "Pass12345!", "Contract Note AI")
    token = registered["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Contract Note Civil", "Contract Note First Project")
    tenant_id = onboarding["tenant_id"]

    response = client.post(
        "/api/ai/workflow/route",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={
            "note": "Vendor: Carolina Haul Services\nScope of Work: Haul export soil and deliver crushed stone\nMaterial Type: crushed stone\nPlan: Continue deliveries tomorrow"
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["routed"] is True
    assert body["processing_outcome"] == "created"
    assert body["customer_created"] is True
    assert body["material_created"] is True
    assert body["report_created"] is True
    assert body["customer_name"] == "Carolina Haul Services"
    assert body["material_name"] == "crushed stone"


def test_ai_routing_recognizes_existing_records_without_duplicates(client: TestClient):
    registered = register_user(client, "existing-ai-route@example.com", "Pass12345!", "Existing AI")
    token = registered["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Existing AI Civil", "Existing AI First Project")
    tenant_id = onboarding["tenant_id"]
    user_id = registered["user_id"]

    with SessionLocal() as db:
        db.add(Customer(tenant_id=tenant_id, name="Summit Peak Builders", created_by=user_id))
        db.add(Material(tenant_id=tenant_id, name="57 stone", created_by=user_id))
        db.commit()

    response = client.post(
        "/api/ai/workflow/route",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"note": "Company: Summit Peak Builders\nMaterial: 57 stone", "project_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["routed"] is True
    assert body["processing_outcome"] == "recognized_existing"
    assert body["created_count"] == 0
    assert body["recognized_existing_count"] == 2
    assert body["message"] == "Recognized 2 existing records; no duplicate rows were created."

    with SessionLocal() as db:
        customers = db.query(Customer).filter(Customer.tenant_id == tenant_id, Customer.name == "Summit Peak Builders").all()
        materials = db.query(Material).filter(Material.tenant_id == tenant_id, Material.name == "57 stone").all()

    assert len(customers) == 1
    assert len(materials) == 1


def test_ai_routing_treats_existing_details_as_usable(client: TestClient):
    registered = register_user(client, "existing-ai-route@example.com", "Pass12345!", "Existing AI")
    token = registered["tokens"]["access_token"]
    onboarding = complete_onboarding(client, token, "Existing AI Civil", "Existing AI First Project")
    tenant_id = onboarding["tenant_id"]
    user_id = registered["user_id"]

    with SessionLocal() as db:
        db.add(Customer(tenant_id=tenant_id, name="Summit Peak Builders", created_by=user_id))
        db.add(Material(tenant_id=tenant_id, name="57 stone", created_by=user_id))
        db.commit()

    response = client.post(
        "/api/ai/workflow/route",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        json={"note": "Summit Peak Builders delivered 57 stone."},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["routed"] is True
    assert body["customer_created"] is False
    assert body["material_created"] is False
    assert body["report_created"] is True
    assert body["processing_outcome"] == "created"
    assert body["recognized_existing_count"] == 2
    assert body["customer_name"] == "Summit Peak Builders"
    assert body["material_name"].lower() == "57 stone"
    assert body["message"] == "Created 1 new record."
