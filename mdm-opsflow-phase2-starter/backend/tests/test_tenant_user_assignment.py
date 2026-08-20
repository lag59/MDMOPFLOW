from fastapi.testclient import TestClient

from .helpers import complete_onboarding, register_user


def test_first_credentialed_user_becomes_owner_and_can_manage_employee_access(client: TestClient):
    founder = register_user(client, "founder-admin@acme.com", "Pass12345!", "Founder Admin")
    founder_token = founder["tokens"]["access_token"]
    onboarding = complete_onboarding(client, founder_token, "Acme Admin Rule", "Admin Rule Project")
    tenant_id = onboarding["tenant_id"]

    members = client.get(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {founder_token}", "X-Tenant-ID": tenant_id},
    )
    assert members.status_code == 200
    founder_row = next((item for item in members.json() if item["email"] == founder["email"]), None)
    assert founder_row is not None
    assert founder_row["role_name"] == "owner"

    employee = register_user(client, "employee-access@acme.com", "Pass12345!", "Employee Access")
    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {founder_token}", "X-Tenant-ID": tenant_id},
        json={"email": employee["email"], "role_name": "project_manager"},
    )
    assert assign.status_code == 201
    employee_user_id = assign.json()["user_id"]

    toggle = client.put(
        f"/api/tenant-users/{employee_user_id}/permissions",
        headers={"Authorization": f"Bearer {founder_token}", "X-Tenant-ID": tenant_id},
        json={"overrides": [{"permission": "billing_read", "enabled": True}]},
    )
    assert toggle.status_code == 200
    assert "billing_read" in toggle.json()["effective_permissions"]


def test_tenant_admin_can_assign_registered_user_to_tenant(client: TestClient):
    owner = register_user(client, "owner@acme.com", "Pass12345!", "Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme", "Acme Project")
    tenant_id = onboarding["tenant_id"]

    member = register_user(client, "member@acme.com", "Pass12345!", "Member User")

    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": member["email"], "role_name": "owner"},
    )
    assert assign.status_code == 201
    assigned = assign.json()
    assert assigned["email"] == member["email"]
    assert assigned["role_name"] == "owner"

    list_members = client.get(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
    )
    assert list_members.status_code == 200
    emails = [item["email"] for item in list_members.json()]
    assert member["email"] in emails


def test_registered_user_is_hidden_until_assigned_to_tenant(client: TestClient):
    owner = register_user(client, "owner-hidden@acme.com", "Pass12345!", "Owner Hidden")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme Hidden", "Hidden Project")
    tenant_id = onboarding["tenant_id"]

    griffin = register_user(client, "griffin@mdmopflow.com", "Pass12345!", "Griffin")

    before_assign = client.get(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
    )
    assert before_assign.status_code == 200
    before_emails = [item["email"] for item in before_assign.json()]
    assert griffin["email"] not in before_emails

    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": griffin["email"], "role_name": "owner"},
    )
    assert assign.status_code == 201

    after_assign = client.get(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
    )
    assert after_assign.status_code == 200
    after_emails = [item["email"] for item in after_assign.json()]
    assert griffin["email"] in after_emails


def test_assigning_standard_role_auto_provisions_missing_tenant_role(client: TestClient):
    owner = register_user(client, "owner2@acme.com", "Pass12345!", "Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme 2", "Acme Project 2")
    tenant_id = onboarding["tenant_id"]

    member = register_user(client, "member2@acme.com", "Pass12345!", "Member User")

    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": member["email"], "role_name": "project_manager"},
    )

    assert assign.status_code == 201
    assigned = assign.json()
    assert assigned["email"] == member["email"]
    assert assigned["role_name"] == "project_manager"


def test_owner_can_create_user_with_temporary_password_and_assign_role(client: TestClient):
    owner = register_user(client, "owner-create@acme.com", "Pass12345!", "Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme Create", "Acme Create Project")
    tenant_id = onboarding["tenant_id"]

    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={
            "email": "newhire@acme.com",
            "role_name": "estimator",
            "display_name": "New Hire",
            "title": "Estimator I",
            "temporary_password": "ChangeMe123!",
        },
    )

    assert assign.status_code == 201
    assigned = assign.json()
    assert assigned["email"] == "newhire@acme.com"
    assert assigned["display_name"] == "New Hire"
    assert assigned["role_name"] == "estimator"

    login = client.post(
        "/api/auth/login",
        json={"email": "newhire@acme.com", "password": "ChangeMe123!", "tenant_id": tenant_id},
    )
    assert login.status_code == 200


def test_owner_can_remove_reactivate_and_reset_tenant_staff_password(client: TestClient):
    owner = register_user(client, "owner-staff-control@acme.com", "Pass12345!", "Owner Staff Control")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme Staff Control", "Staff Control Project")
    tenant_id = onboarding["tenant_id"]

    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={
            "email": "staff-control@acme.com",
            "role_name": "field_supervisor",
            "display_name": "Staff Control",
            "temporary_password": "ChangeMe123!",
        },
    )
    assert assign.status_code == 201, assign.text
    user_id = assign.json()["user_id"]

    reset = client.post(
        f"/api/tenant-users/{user_id}/reset-password",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"new_password": "OwnerReset123!"},
    )
    assert reset.status_code == 200, reset.text

    new_login = client.post(
        "/api/auth/login",
        json={"email": "staff-control@acme.com", "password": "OwnerReset123!", "tenant_id": tenant_id},
    )
    assert new_login.status_code == 200

    remove = client.patch(
        f"/api/tenant-users/{user_id}/membership",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"status": "inactive"},
    )
    assert remove.status_code == 200, remove.text
    assert remove.json()["status"] == "inactive"

    denied_after_remove = client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {new_login.json()['tokens']['access_token']}", "X-Tenant-ID": tenant_id},
    )
    assert denied_after_remove.status_code == 403

    list_after_remove = client.get(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
    )
    assert list_after_remove.status_code == 200
    removed_row = next(item for item in list_after_remove.json() if item["email"] == "staff-control@acme.com")
    assert removed_row["status"] == "inactive"

    reactivate = client.patch(
        f"/api/tenant-users/{user_id}/membership",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"role_name": "field_supervisor", "status": "active"},
    )
    assert reactivate.status_code == 200, reactivate.text
    assert reactivate.json()["status"] == "active"


def test_owner_cannot_remove_last_active_owner_membership(client: TestClient):
    owner = register_user(client, "owner-last-owner@acme.com", "Pass12345!", "Owner Last Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme Last Owner", "Last Owner Project")
    tenant_id = onboarding["tenant_id"]

    remove_owner = client.patch(
        f"/api/tenant-users/{owner['user_id']}/membership",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"status": "inactive"},
    )
    assert remove_owner.status_code == 400
    assert "last active owner" in remove_owner.json()["detail"]


def test_assigning_case_variant_reuses_existing_user_account(client: TestClient):
    owner = register_user(client, "owner-case@acme.com", "Pass12345!", "Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme Case", "Acme Case Project")
    tenant_id = onboarding["tenant_id"]

    existing = register_user(client, "CaseMember@acme.com", "Pass12345!", "Case Member")

    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": "casemember@acme.com", "role_name": "project_manager"},
    )

    assert assign.status_code == 201
    assert assign.json()["email"] == "casemember@acme.com"
    assert assign.json()["user_id"] == existing["user_id"]


def test_owner_can_toggle_user_permissions(client: TestClient):
    owner = register_user(client, "owner3@acme.com", "Pass12345!", "Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme 3", "Acme Project 3")
    tenant_id = onboarding["tenant_id"]

    member = register_user(client, "member3@acme.com", "Pass12345!", "Member User")
    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": member["email"], "role_name": "project_manager"},
    )
    assert assign.status_code == 201
    user_id = assign.json()["user_id"]

    before = client.get(
        f"/api/tenant-users/{user_id}/permissions",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
    )
    assert before.status_code == 200
    before_body = before.json()
    assert "intake_write" in before_body["effective_permissions"]
    assert "billing_read" not in before_body["effective_permissions"]

    update = client.put(
        f"/api/tenant-users/{user_id}/permissions",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={
            "overrides": [
                {"permission": "intake_write", "enabled": False},
                {"permission": "billing_read", "enabled": True},
            ]
        },
    )
    assert update.status_code == 200
    update_body = update.json()
    assert "intake_write" not in update_body["effective_permissions"]
    assert "billing_read" in update_body["effective_permissions"]

    overrides = {item["permission"]: item["enabled"] for item in update_body["overrides"]}
    assert overrides["intake_write"] is False
    assert overrides["billing_read"] is True


def test_permission_toggle_rejects_unknown_permissions(client: TestClient):
    owner = register_user(client, "owner4@acme.com", "Pass12345!", "Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme 4", "Acme Project 4")
    tenant_id = onboarding["tenant_id"]

    member = register_user(client, "member4@acme.com", "Pass12345!", "Member User")
    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": member["email"], "role_name": "project_manager"},
    )
    assert assign.status_code == 201
    user_id = assign.json()["user_id"]

    update = client.put(
        f"/api/tenant-users/{user_id}/permissions",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"overrides": [{"permission": "not_a_real_permission", "enabled": True}]},
    )
    assert update.status_code == 400
    assert "Unknown permissions" in update.json()["detail"]


def test_super_admin_can_manage_tenant_users_without_membership(client: TestClient):
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "founder@mdmopsflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    owner = register_user(client, "owner-superadmin-tenant@acme.com", "Pass12345!", "Owner Superadmin Tenant")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme Superadmin", "Acme Superadmin Project")
    tenant_id = onboarding["tenant_id"]

    list_members = client.get(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": tenant_id},
    )
    assert list_members.status_code == 200

    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": tenant_id},
        json={
            "email": "superadmin-created-estimator@acme.com",
            "role_name": "estimator",
            "display_name": "Created By Super Admin",
            "temporary_password": "ChangeMe123!",
        },
    )
    assert assign.status_code == 201, assign.text
    assigned_user_id = assign.json()["user_id"]

    update_permissions = client.put(
        f"/api/tenant-users/{assigned_user_id}/permissions",
        headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": tenant_id},
        json={"overrides": [{"permission": "billing_read", "enabled": True}]},
    )
    assert update_permissions.status_code == 200
    assert "billing_read" in update_permissions.json()["effective_permissions"]


def test_owner_cannot_assign_tenant_admin_role(client: TestClient):
    owner = register_user(client, "owner-no-admin-grant@acme.com", "Pass12345!", "Owner No Admin Grant")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme Owner Policy", "Owner Policy Project")
    tenant_id = onboarding["tenant_id"]

    member = register_user(client, "member-no-admin-grant@acme.com", "Pass12345!", "Member No Admin Grant")

    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": member["email"], "role_name": "tenant_admin"},
    )
    assert assign.status_code == 403
    assert "cannot grant administrative tenant roles" in assign.json()["detail"]


def test_owner_cannot_enable_admin_grade_permissions(client: TestClient):
    owner = register_user(client, "owner-no-admin-perm@acme.com", "Pass12345!", "Owner No Admin Perm")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Acme Owner Perms", "Owner Perms Project")
    tenant_id = onboarding["tenant_id"]

    member = register_user(client, "member-no-admin-perm@acme.com", "Pass12345!", "Member No Admin Perm")
    assign = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"email": member["email"], "role_name": "project_manager"},
    )
    assert assign.status_code == 201
    user_id = assign.json()["user_id"]

    update = client.put(
        f"/api/tenant-users/{user_id}/permissions",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={"overrides": [{"permission": "admin_write", "enabled": True}]},
    )
    assert update.status_code == 403
    assert "cannot grant administrative permissions" in update.json()["detail"]
