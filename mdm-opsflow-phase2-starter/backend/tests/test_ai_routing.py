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
    assert body["material_created"] is True
    assert body["material_name"] == "57 stone"
