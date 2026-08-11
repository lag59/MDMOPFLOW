from fastapi.testclient import TestClient

from app.rbac import (
    FORMAL_PERMISSION_CATALOG,
    LEGACY_PERMISSION_REQUIREMENTS,
    ROLE_PERMISSION_MATRIX,
    resolve_permissions,
)
from tests.helpers import complete_onboarding, register_user


EXPECTED_TENANT_ROLES = {
    "accounting",
    "administrator",
    "customer",
    "dispatcher",
    "estimator",
    "executive",
    "field_supervisor",
    "fleet_manager",
    "owner",
    "payroll",
    "project_manager",
    "safety_manager",
    "tenant_admin",
    "vendor",
}


ROLE_EXPECTED_GRANULAR: dict[str, set[str]] = {
    "accounting": {"finance.view", "finance.manage", "billing.view", "billing.manage", "project.view", "estimate.view"},
    "administrator": {"user.view", "user.manage", "membership.assign", "project.manage", "billing.manage"},
    "customer": {"portal.customer.view", "project.view"},
    "dispatcher": {"dispatch.view", "dispatch.manage", "fleet.view"},
    "estimator": {"estimate.view", "estimate.create", "estimate.edit", "project.view"},
    "executive": {"project.view", "finance.view", "payroll.view"},
    "field_supervisor": {"project.manage", "safety.manage", "dispatch.view"},
    "fleet_manager": {"fleet.view", "fleet.manage", "dispatch.manage"},
    "owner": {"project.approve", "membership.assign", "billing.manage"},
    "payroll": {"payroll.view", "payroll.process"},
    "project_manager": {"project.manage", "estimate.create", "estimate.edit", "dispatch.manage"},
    "safety_manager": {"safety.view", "safety.manage"},
    "tenant_admin": {"project.manage", "estimate.edit", "membership.assign", "fleet.manage", "safety.manage"},
    "vendor": {"portal.vendor.submit", "project.view"},
}


def test_formal_permission_catalog_has_required_granular_entries() -> None:
    for permission in [
        "estimate.create",
        "estimate.edit",
        "project.view",
        "project.manage",
        "payroll.view",
        "payroll.process",
        "user.manage",
        "membership.assign",
        "fleet.manage",
        "safety.manage",
    ]:
        assert permission in FORMAL_PERMISSION_CATALOG


def test_role_permission_matrix_covers_all_14_deployed_roles() -> None:
    matrix_roles = set(ROLE_PERMISSION_MATRIX.keys()) - {"platform_super_admin"}
    assert matrix_roles == EXPECTED_TENANT_ROLES



def test_each_role_has_expected_granular_permissions() -> None:
    for role_name, expected_permissions in ROLE_EXPECTED_GRANULAR.items():
        actual_permissions = set(ROLE_PERMISSION_MATRIX[role_name])
        missing = expected_permissions - actual_permissions
        assert not missing, f"Role {role_name} missing expected permissions: {sorted(missing)}"



def test_legacy_aliases_still_resolve_for_existing_route_guards() -> None:
    resolved = resolve_permissions("tenant_admin", None)
    for legacy_name in LEGACY_PERMISSION_REQUIREMENTS:
        if legacy_name in {"portal_customer_read", "portal_vendor_write"}:
            # tenant_admin is intentionally not granted these portal-specific permissions.
            continue
        assert legacy_name in resolved, f"Missing legacy alias {legacy_name} in resolved permissions"



def test_tenant_admin_catalog_api_requires_admin_read_and_returns_matrix(client: TestClient) -> None:
    owner = register_user(client, "catalog-owner@example.com", "Pass12345!", "Catalog Owner")
    owner_token = owner["tokens"]["access_token"]
    onboarding = complete_onboarding(client, owner_token, "Catalog Tenant", "Catalog Project")
    tenant_id = onboarding["tenant_id"]

    allowed = client.get(
        "/api/tenant-users/permissions/formal-catalog",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
    )
    assert allowed.status_code == 200, allowed.text
    payload = allowed.json()
    for role in EXPECTED_TENANT_ROLES:
        assert role in payload["role_matrix"]

    customer = register_user(client, "catalog-customer@example.com", "Pass12345!", "Catalog Customer")
    customer_token = customer["tokens"]["access_token"]

    assign_customer = client.post(
        "/api/tenant-users",
        headers={"Authorization": f"Bearer {owner_token}", "X-Tenant-ID": tenant_id},
        json={
            "email": "catalog-customer@example.com",
            "role_name": "customer",
            "display_name": "Catalog Customer",
            "title": "Customer",
            "temporary_password": "Pass12345!",
        },
    )
    assert assign_customer.status_code == 201, assign_customer.text

    denied = client.get(
        "/api/tenant-users/permissions/formal-catalog",
        headers={"Authorization": f"Bearer {customer_token}", "X-Tenant-ID": tenant_id},
    )
    assert denied.status_code == 403



def test_platform_admin_catalog_api_exposed_for_super_admin(client: TestClient) -> None:
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "founder@mdmopsflow.com", "password": "ChangeMe123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["tokens"]["access_token"]

    response = client.get(
        "/api/admin/permissions/formal-catalog",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload["role_matrix"].keys()) == EXPECTED_TENANT_ROLES
    assert "estimate.create" in payload["permissions"]
