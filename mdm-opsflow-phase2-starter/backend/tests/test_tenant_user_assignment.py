from fastapi.testclient import TestClient

from .helpers import complete_onboarding, register_user


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
