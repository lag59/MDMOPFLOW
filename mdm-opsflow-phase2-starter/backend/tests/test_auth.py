from fastapi.testclient import TestClient
from sqlalchemy import func

from app.db import SessionLocal
from app.models import MembershipStatus, Role, Tenant, TenantMembership, User


def test_tenant_names_are_normalized_for_canonical_seed_lookup(client: TestClient):
    register = client.post(
        "/api/auth/register",
        json={"email": "tenant-normalize@example.com", "password": "Pass12345!", "display_name": "Tenant Normalize"},
    )
    assert register.status_code == 201
    token = register.json()["tokens"]["access_token"]

    first = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "company_name": "  ACME CIVIL  ",
            "company_types": ["Heavy Civil"],
            "language": "en",
            "modules": ["Projects"],
            "invite_emails": [],
            "first_project_name": "Acme Project",
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "company_name": "acme civil",
            "company_types": ["Heavy Civil"],
            "language": "en",
            "modules": ["Projects"],
            "invite_emails": [],
            "first_project_name": "Duplicate Project",
        },
    )
    assert second.status_code == 400
    with SessionLocal() as db:
        matches = db.query(Tenant).filter(func.lower(Tenant.name) == "acme civil").all()
        assert len(matches) == 1
        assert matches[0].name == "ACME CIVIL" or matches[0].name == "Acme Civil"


def test_auth_register_login_me_refresh_logout(client: TestClient):
    payload = {
        "email": "auth-user@example.com",
        "password": "Pass12345!",
        "display_name": "Auth User",
    }

    register_response = client.post("/api/auth/register", json=payload)
    assert register_response.status_code == 201
    register_data = register_response.json()
    assert register_data["email"] == payload["email"]
    assert register_data["tokens"]["access_token"]
    assert register_data["tokens"]["refresh_token"]

    login_response = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    access_token = login_data["tokens"]["access_token"]
    refresh_token = login_data["tokens"]["refresh_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == payload["email"]

    update_me_response = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"display_name": "Updated Auth User", "title": "PM"},
    )
    assert update_me_response.status_code == 200
    assert update_me_response.json()["display_name"] == "Updated Auth User"
    assert update_me_response.json()["title"] == "PM"

    refresh_response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["access_token"]
    assert refreshed["refresh_token"]

    logout_response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert logout_response.status_code == 204

    refresh_after_logout = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_after_logout.status_code == 401


def test_owner_can_complete_onboarding_with_only_invited_or_inactive_membership(client: TestClient):
    register = client.post(
        "/api/auth/register",
        json={"email": "owner-invited@example.com", "password": "Pass12345!", "display_name": "Owner Invited"},
    )
    assert register.status_code == 201
    token = register.json()["tokens"]["access_token"]

    with SessionLocal() as db:
        tenant = Tenant(name="Invited Tenant", company_type="General Contractor", preferred_language="en")
        db.add(tenant)
        db.flush()

        role = Role(tenant_id=tenant.id, name="owner", permissions="project.manage", created_by=register.json()["user_id"])
        db.add(role)
        db.flush()

        db.add(
            TenantMembership(
                tenant_id=tenant.id,
                user_id=register.json()["user_id"],
                role_id=role.id,
                status=MembershipStatus.INVITED,
                created_by=register.json()["user_id"],
            )
        )
        db.commit()

    response = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "company_name": "New Owner Company",
            "company_types": ["Heavy Civil"],
            "language": "en",
            "modules": ["Projects"],
            "invite_emails": [],
            "first_project_name": "New Owner Project",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["tenant_id"]


def test_super_admin_login_recovers_when_seed_user_is_missing(client: TestClient):
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "lag59@mdmopflow.com").first()
        if user:
            db.delete(user)
            db.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "lag59@mdmopflow.com", "password": "ChangeMe123!"},
    )
    assert response.status_code == 200
    assert response.json()["platform_role"] == "platform_super_admin"


def test_super_admin_email_is_normalized_to_single_canonical_identity(client: TestClient):
    with SessionLocal() as db:
        db.query(User).filter(User.email.ilike("lag59@mdmopflow.com")).delete()
        legacy_alias = User(
            email="lag59@mdmopflow.com",
            password_hash="legacy-hash",
            display_name="Legacy Super Admin",
            title="Legacy",
            platform_role=User.__table__.c.get("platform_role") if False else None,
        )
        db.add(legacy_alias)
        db.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "LAG59@MDMOPFLOW.COM", "password": "ChangeMe123!"},
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        rows = db.query(User).filter(User.email.ilike("lag59@mdmopflow.com")).all()
        assert len(rows) == 1
        assert rows[0].email == "lag59@mdmopflow.com"


def test_login_accepts_case_variant_of_registered_email(client: TestClient):
    register_response = client.post(
        "/api/auth/register",
        json={"email": "CaseUser@example.com", "password": "Pass12345!", "display_name": "Case User"},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"email": "caseuser@example.com", "password": "Pass12345!"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["email"] == "caseuser@example.com"


def test_platform_admin_is_seeded_and_protected(client: TestClient):
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "lag59@mdmopflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    overview = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert overview.status_code == 200
    assert overview.json()["role"] == "platform_super_admin"

    user_register = client.post(
        "/api/auth/register",
        json={"email": "regular@example.com", "password": "Pass12345!", "display_name": "Regular"},
    )
    user_token = user_register.json()["tokens"]["access_token"]

    denied = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {user_token}"})
    assert denied.status_code == 403


def test_super_admin_can_manage_user_access_and_reset_password(client: TestClient):
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "lag59@mdmopflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    user_register = client.post(
        "/api/auth/register",
        json={"email": "managed-user@example.com", "password": "Pass12345!", "display_name": "Managed User"},
    )
    assert user_register.status_code == 201
    user_id = user_register.json()["user_id"]

    users_list = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert users_list.status_code == 200
    assert any(row["email"] == "managed-user@example.com" for row in users_list.json())

    access_update = client.patch(
        f"/api/admin/users/{user_id}/access",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"platform_role": "platform_super_admin", "is_active": True},
    )
    assert access_update.status_code == 200
    assert access_update.json()["platform_role"] == "platform_super_admin"

    password_reset = client.post(
        f"/api/admin/users/{user_id}/reset-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"new_password": "ResetPass123!"},
    )
    assert password_reset.status_code == 200

    old_login = client.post(
        "/api/auth/login",
        json={"email": "managed-user@example.com", "password": "Pass12345!"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={"email": "managed-user@example.com", "password": "ResetPass123!"},
    )
    assert new_login.status_code == 200


def test_super_admin_can_create_tenant_and_assign_user_membership(client: TestClient):
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "lag59@mdmopflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    create_tenant = client.post(
        "/api/admin/tenants",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "tenant_name": "Tenant Created By Super Admin",
            "company_type": "Heavy Civil",
            "preferred_language": "en",
            "selected_modules": ["Projects", "Budget"],
        },
    )
    assert create_tenant.status_code == 201, create_tenant.text
    tenant_id = create_tenant.json()["tenant_id"]

    managed_user = client.post(
        "/api/auth/register",
        json={"email": "tenant-assigned@example.com", "password": "Pass12345!", "display_name": "Tenant Assigned"},
    )
    assert managed_user.status_code == 201
    managed_user_id = managed_user.json()["user_id"]

    assign = client.post(
        f"/api/admin/users/{managed_user_id}/memberships",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tenant_id": tenant_id, "role_name": "owner"},
    )
    assert assign.status_code == 201, assign.text
    assert assign.json()["status"] == "active"


def test_membership_activation_reenables_user_login(client: TestClient):
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "lag59@mdmopflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    owner = client.post(
        "/api/auth/register",
        json={"email": "owner-activation@acme.com", "password": "Pass12345!", "display_name": "Owner Activation"},
    )
    assert owner.status_code == 201
    owner_token = owner.json()["tokens"]["access_token"]

    onboarding = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "company_name": "Activation Tenant",
            "company_types": ["Heavy Civil"],
            "language": "en",
            "modules": ["Projects", "Budget"],
            "invite_emails": [],
            "first_project_name": "Activation Project",
        },
    )
    assert onboarding.status_code == 201
    tenant_id = onboarding.json()["tenant_id"]

    member = client.post(
        "/api/auth/register",
        json={"email": "inactive-member@acme.com", "password": "Pass12345!", "display_name": "Inactive Member"},
    )
    assert member.status_code == 201
    member_id = member.json()["user_id"]

    deactivate = client.patch(
        f"/api/admin/users/{member_id}/access",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    assign = client.post(
        f"/api/admin/users/{member_id}/memberships",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tenant_id": tenant_id, "role_name": "estimator"},
    )
    assert assign.status_code == 201

    login = client.post(
        "/api/auth/login",
        json={"email": "inactive-member@acme.com", "password": "Pass12345!", "tenant_id": tenant_id},
    )
    assert login.status_code == 200


def test_membership_deactivation_revokes_tenant_access_and_reactivation_restores_it(client: TestClient):
    owner = client.post(
        "/api/auth/register",
        json={"email": "owner-inactive-membership@acme.com", "password": "Pass12345!", "display_name": "Owner Inactive Membership"},
    )
    assert owner.status_code == 201
    owner_token = owner.json()["tokens"]["access_token"]

    onboarding = client.post(
        "/api/onboarding/complete",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "company_name": "Inactive Membership Tenant",
            "company_types": ["Heavy Civil"],
            "language": "en",
            "modules": ["Projects", "Budget"],
            "invite_emails": [],
            "first_project_name": "Inactive Membership Project",
        },
    )
    assert onboarding.status_code == 201
    tenant_id = onboarding.json()["tenant_id"]

    member = client.post(
        "/api/auth/register",
        json={"email": "inactive-membership-user@acme.com", "password": "Pass12345!", "display_name": "Inactive Membership User"},
    )
    assert member.status_code == 201
    member_token = member.json()["tokens"]["access_token"]

    assign_member = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": "inactive-membership-user@acme.com", "role_name": "project_manager"},
    )
    assert assign_member.status_code == 201

    member_headers = {"Authorization": f"Bearer {member_token}", "X-Tenant-ID": tenant_id}
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id}

    projects_before = client.get(
        "/api/projects",
        headers=member_headers,
    )
    assert projects_before.status_code == 200
    project_id = projects_before.json()[0]["id"]

    create_estimate = client.post(
        "/api/estimates",
        headers=member_headers,
        json={
            "project_id": project_id,
            "estimate_name": "Membership Transition Estimate",
            "estimate_number": "MT-EST-001",
            "customer_name": "Transition Customer",
            "project_name": "Inactive Membership Project",
            "project_address": "100 Transition Way",
            "project_type": "Civil",
            "estimator_name": "Inactive Membership User",
            "status": "Draft Estimate",
        },
    )
    assert create_estimate.status_code == 201, create_estimate.text
    estimate_id = create_estimate.json()["id"]

    create_ticket = client.post(
        "/api/tickets",
        headers=member_headers,
        json={
            "project_id": project_id,
            "ticket_number": "MT-TCK-001",
            "truck": "TR-001",
            "driver": "Alex Driver",
            "material": "Aggregate Base",
            "status": "draft",
        },
    )
    assert create_ticket.status_code == 201, create_ticket.text
    ticket_id = create_ticket.json()["id"]

    memberships = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert memberships.status_code == 200
    assert any(item["tenant_id"] == tenant_id for item in memberships.json()["memberships"])

    admin_login = client.post(
        "/api/auth/login",
        json={"email": "lag59@mdmopflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    member_rows = client.get(
        f"/api/admin/users/{assign_member.json()['user_id']}/memberships",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert member_rows.status_code == 200
    row = next(item for item in member_rows.json() if item["tenant_id"] == tenant_id and item["status"] == "active")

    deactivate_membership = client.patch(
        f"/api/admin/users/{assign_member.json()['user_id']}/memberships/{row['membership_id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tenant_id": tenant_id, "role_name": "project_manager", "status": "inactive"},
    )
    assert deactivate_membership.status_code == 200

    denied = client.get(
        "/api/projects",
        headers=member_headers,
    )
    assert denied.status_code == 403

    memberships_after_deactivation = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert memberships_after_deactivation.status_code == 200
    assert all(item["tenant_id"] != tenant_id for item in memberships_after_deactivation.json()["memberships"])

    owner_project = client.get(f"/api/projects/{project_id}", headers=owner_headers)
    assert owner_project.status_code == 200

    owner_estimate = client.get(f"/api/estimates/{estimate_id}", headers=owner_headers)
    assert owner_estimate.status_code == 200
    assert owner_estimate.json()["project_id"] == project_id

    owner_ticket = client.get(f"/api/tickets/{ticket_id}", headers=owner_headers)
    assert owner_ticket.status_code == 200
    assert owner_ticket.json()["project_id"] == project_id

    audit_logs = client.get(
        "/api/admin/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert audit_logs.status_code == 200
    assert any(
        entry["action"] == "admin_update_user_membership" and entry["resource_id"] == row["membership_id"]
        for entry in audit_logs.json()
    )

    reactivate_membership = client.patch(
        f"/api/admin/users/{assign_member.json()['user_id']}/memberships/{row['membership_id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tenant_id": tenant_id, "role_name": "project_manager", "status": "active"},
    )
    assert reactivate_membership.status_code == 200

    allowed_after_reactivation = client.get(
        "/api/projects",
        headers=member_headers,
    )
    assert allowed_after_reactivation.status_code == 200

    memberships_after_reactivation = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert memberships_after_reactivation.status_code == 200
    assert any(item["tenant_id"] == tenant_id for item in memberships_after_reactivation.json()["memberships"])


def test_inactive_user_cannot_login(client: TestClient):
    register_response = client.post(
        "/api/auth/register",
        json={"email": "inactive-login@example.com", "password": "Pass12345!", "display_name": "Inactive Login"},
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["user_id"]

    admin_login = client.post(
        "/api/auth/login",
        json={"email": "lag59@mdmopflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    deactivate = client.patch(
        f"/api/admin/users/{user_id}/access",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert deactivate.status_code == 200

    login = client.post(
        "/api/auth/login",
        json={"email": "inactive-login@example.com", "password": "Pass12345!"},
    )
    assert login.status_code == 401
    assert login.json()["detail"] == "Account is inactive"
