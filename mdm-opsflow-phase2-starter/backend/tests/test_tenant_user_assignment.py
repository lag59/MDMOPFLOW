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
