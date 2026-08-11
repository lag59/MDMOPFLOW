from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import logging

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


@dataclass
class AuthorizationResource:
    tenant_id: str | None = None
    owner_user_id: str | None = None
    workflow_state: str | None = None


def _as_resource(resource: AuthorizationResource | Any | None) -> AuthorizationResource | None:
    if resource is None:
        return None
    if isinstance(resource, AuthorizationResource):
        return resource
    return AuthorizationResource(
        tenant_id=getattr(resource, "tenant_id", None),
        owner_user_id=getattr(resource, "owner_user_id", None)
        or getattr(resource, "created_by", None)
        or getattr(resource, "user_id", None),
        workflow_state=getattr(resource, "workflow_state", None) or getattr(resource, "status", None),
    )


def authorize_action(
    *,
    user: Any,
    tenant_id: str | None,
    permission: str | None,
    resource: AuthorizationResource | Any | None = None,
    membership: Any | None = None,
    permissions: set[str] | None = None,
    tenant_roles: set[str] | None = None,
    require_membership: bool = True,
    required_membership_state: str = "active",
    allowed_roles: set[str] | None = None,
    require_owner: bool = False,
    allowed_workflow_states: set[str] | None = None,
    missing_tenant_status: int = status.HTTP_400_BAD_REQUEST,
    missing_tenant_detail: str = "X-Tenant-ID is required for platform admins",
    membership_required_detail: str = "Tenant membership required",
    permission_denied_detail: str = "Insufficient permissions",
    tenant_mismatch_status: int = status.HTTP_403_FORBIDDEN,
    tenant_mismatch_detail: str = "Tenant access denied",
    resource_tenant_mismatch_status: int = status.HTTP_404_NOT_FOUND,
    resource_tenant_mismatch_detail: str = "Resource not found",
    ownership_mismatch_status: int = status.HTTP_403_FORBIDDEN,
    ownership_mismatch_detail: str = "Resource ownership required",
    workflow_denied_status: int = status.HTTP_409_CONFLICT,
    workflow_denied_detail: str = "Invalid workflow state",
    role_denied_status: int = status.HTTP_403_FORBIDDEN,
    role_denied_detail: str = "Role not authorized for this action",
) -> str:
    """Centralized authorization decision engine.

    Returns the resolved tenant scope on success and raises HTTPException on deny.
    """

    effective_permissions = permissions or set()
    is_super_admin = "*" in effective_permissions

    if permission and not is_super_admin and permission not in effective_permissions:
        logger.warning(
            "authorization_denied",
            extra={
                "reason": "missing_permission",
                "required_permission": permission,
                "tenant_id": tenant_id,
            },
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=permission_denied_detail)

    resolved_tenant_id: str | None = None
    if is_super_admin:
        resolved_tenant_id = tenant_id
        if require_membership and not resolved_tenant_id:
            raise HTTPException(status_code=missing_tenant_status, detail=missing_tenant_detail)
    else:
        membership_tenant_id = getattr(membership, "tenant_id", None)
        membership_state = getattr(membership, "status", None)
        if require_membership and not membership_tenant_id:
            logger.warning("authorization_denied", extra={"reason": "missing_membership", "tenant_id": tenant_id})
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=membership_required_detail)
        if require_membership and required_membership_state and membership_state is not None:
            normalized_membership_state = (
                str(getattr(membership_state, "value", membership_state)).strip().lower()
            )
            if normalized_membership_state != required_membership_state.lower():
                logger.warning(
                    "authorization_denied",
                    extra={
                        "reason": "inactive_membership",
                        "membership_state": normalized_membership_state,
                        "required_state": required_membership_state.lower(),
                    },
                )
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=membership_required_detail)
        if membership_tenant_id is not None:
            resolved_tenant_id = membership_tenant_id
            if tenant_id and tenant_id != membership_tenant_id:
                logger.warning(
                    "authorization_denied",
                    extra={
                        "reason": "tenant_mismatch",
                        "requested_tenant_id": tenant_id,
                        "membership_tenant_id": membership_tenant_id,
                    },
                )
                raise HTTPException(status_code=tenant_mismatch_status, detail=tenant_mismatch_detail)

        if allowed_roles is not None:
            caller_roles = {role.lower() for role in (tenant_roles or set())}
            if not caller_roles.intersection({role.lower() for role in allowed_roles}):
                logger.warning(
                    "authorization_denied",
                    extra={"reason": "role_not_allowed", "allowed_roles": sorted(allowed_roles)},
                )
                raise HTTPException(status_code=role_denied_status, detail=role_denied_detail)

    resource_ctx = _as_resource(resource)
    if resource_ctx and resource_ctx.tenant_id and resolved_tenant_id and resource_ctx.tenant_id != resolved_tenant_id:
        logger.warning(
            "authorization_denied",
            extra={
                "reason": "resource_tenant_mismatch",
                "resource_tenant_id": resource_ctx.tenant_id,
                "resolved_tenant_id": resolved_tenant_id,
            },
        )
        raise HTTPException(status_code=resource_tenant_mismatch_status, detail=resource_tenant_mismatch_detail)

    if require_owner and resource_ctx and resource_ctx.owner_user_id and getattr(user, "id", None) != resource_ctx.owner_user_id:
        logger.warning("authorization_denied", extra={"reason": "ownership_required"})
        raise HTTPException(status_code=ownership_mismatch_status, detail=ownership_mismatch_detail)

    if allowed_workflow_states is not None and resource_ctx is not None:
        if resource_ctx.workflow_state not in allowed_workflow_states:
            logger.warning(
                "authorization_denied",
                extra={
                    "reason": "workflow_state_blocked",
                    "workflow_state": resource_ctx.workflow_state,
                    "allowed_workflow_states": sorted(allowed_workflow_states),
                },
            )
            raise HTTPException(status_code=workflow_denied_status, detail=workflow_denied_detail)

    if require_membership and not resolved_tenant_id:
        logger.warning("authorization_denied", extra={"reason": "missing_tenant_scope"})
        raise HTTPException(status_code=missing_tenant_status, detail=missing_tenant_detail)

    return resolved_tenant_id or ""
