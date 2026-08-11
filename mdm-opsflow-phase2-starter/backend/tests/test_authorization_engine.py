from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.authorization import AuthorizationResource, authorize_action
from app.dependencies import RequestContext, ensure_tenant_resource_access, resolve_tenant_scope


def _user(user_id: str) -> SimpleNamespace:
    return SimpleNamespace(id=user_id)


def _membership(tenant_id: str) -> SimpleNamespace:
    return SimpleNamespace(tenant_id=tenant_id, status="active")


def test_authorize_action_allows_super_admin_with_explicit_tenant_scope() -> None:
    tenant_id = authorize_action(
        user=_user("admin"),
        tenant_id="tenant-a",
        permission="project_read",
        membership=None,
        permissions={"*"},
        require_membership=True,
    )
    assert tenant_id == "tenant-a"


def test_authorize_action_denies_missing_permission_for_member() -> None:
    with pytest.raises(HTTPException) as exc:
        authorize_action(
            user=_user("u1"),
            tenant_id="tenant-a",
            permission="project_write",
            membership=_membership("tenant-a"),
            permissions={"project_read"},
            require_membership=True,
        )
    assert exc.value.status_code == 403


def test_authorize_action_denies_cross_tenant_scope_for_member() -> None:
    with pytest.raises(HTTPException) as exc:
        authorize_action(
            user=_user("u1"),
            tenant_id="tenant-b",
            permission="project_read",
            membership=_membership("tenant-a"),
            permissions={"project_read"},
            require_membership=True,
            tenant_mismatch_detail="Tenant access denied",
        )
    assert exc.value.status_code == 403


def test_authorize_action_hides_resource_on_cross_tenant_access() -> None:
    with pytest.raises(HTTPException) as exc:
        authorize_action(
            user=_user("u1"),
            tenant_id="tenant-a",
            permission="project_read",
            resource=AuthorizationResource(tenant_id="tenant-b"),
            membership=_membership("tenant-a"),
            permissions={"project_read"},
            resource_tenant_mismatch_status=404,
            resource_tenant_mismatch_detail="Project not found",
        )
    assert exc.value.status_code == 404


def test_authorize_action_enforces_resource_owner_when_required() -> None:
    with pytest.raises(HTTPException) as exc:
        authorize_action(
            user=_user("u1"),
            tenant_id="tenant-a",
            permission="estimate_write",
            resource=AuthorizationResource(tenant_id="tenant-a", owner_user_id="u2"),
            membership=_membership("tenant-a"),
            permissions={"estimate_write"},
            require_owner=True,
        )
    assert exc.value.status_code == 403


def test_authorize_action_enforces_workflow_state() -> None:
    with pytest.raises(HTTPException) as exc:
        authorize_action(
            user=_user("u1"),
            tenant_id="tenant-a",
            permission="estimate_write",
            resource=AuthorizationResource(tenant_id="tenant-a", workflow_state="submitted"),
            membership=_membership("tenant-a"),
            permissions={"estimate_write"},
            allowed_workflow_states={"draft", "returned"},
        )
    assert exc.value.status_code == 409


def test_authorize_action_allows_when_workflow_state_is_permitted() -> None:
    tenant_id = authorize_action(
        user=_user("u1"),
        tenant_id="tenant-a",
        permission="estimate_write",
        resource=AuthorizationResource(tenant_id="tenant-a", workflow_state="draft"),
        membership=_membership("tenant-a"),
        permissions={"estimate_write"},
        allowed_workflow_states={"draft", "returned"},
    )
    assert tenant_id == "tenant-a"


def test_authorize_action_denies_inactive_membership_state() -> None:
    with pytest.raises(HTTPException) as exc:
        authorize_action(
            user=_user("u1"),
            tenant_id="tenant-a",
            permission="project_read",
            membership=SimpleNamespace(tenant_id="tenant-a", status="inactive"),
            permissions={"project_read"},
            require_membership=True,
        )
    assert exc.value.status_code == 403


def test_authorize_action_denies_when_tenant_role_not_allowed() -> None:
    with pytest.raises(HTTPException) as exc:
        authorize_action(
            user=_user("u1"),
            tenant_id="tenant-a",
            permission="admin_write",
            membership=_membership("tenant-a"),
            permissions={"admin_write"},
            tenant_roles={"estimator"},
            allowed_roles={"owner", "tenant_admin"},
        )
    assert exc.value.status_code == 403


def test_authorize_action_allows_when_tenant_role_is_allowed() -> None:
    tenant_id = authorize_action(
        user=_user("u1"),
        tenant_id="tenant-a",
        permission="admin_write",
        membership=_membership("tenant-a"),
        permissions={"admin_write"},
        tenant_roles={"owner"},
        allowed_roles={"owner", "tenant_admin"},
    )
    assert tenant_id == "tenant-a"


def test_resolve_tenant_scope_and_resource_access_helpers() -> None:
    context = RequestContext(
        user=_user("u1"),
        membership=_membership("tenant-a"),
        permissions={"project_read"},
        tenant_id="tenant-a",
    )

    assert resolve_tenant_scope(context, "tenant-a") == "tenant-a"

    with pytest.raises(HTTPException) as exc:
        resolve_tenant_scope(context, "tenant-b")
    assert exc.value.status_code == 403

    ensure_tenant_resource_access(
        resource_tenant_id="tenant-a",
        context=context,
        not_found_detail="Project not found",
    )

    with pytest.raises(HTTPException) as exc2:
        ensure_tenant_resource_access(
            resource_tenant_id="tenant-b",
            context=context,
            not_found_detail="Project not found",
        )
    assert exc2.value.status_code == 404
