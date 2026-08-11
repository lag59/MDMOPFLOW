from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
import logging

from app.authorization import AuthorizationResource, authorize_action
from app.db import get_db
from app.models import MembershipStatus, PlatformRole, Role, Tenant, TenantMembership, User, UserPermissionOverride
from app.observability import bind_identity
from app.rbac import resolve_permissions
from app.security import TokenError, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
logger = logging.getLogger(__name__)


class RequestContext:
    def __init__(
        self,
        user: User,
        membership: TenantMembership | None,
        permissions: set[str],
        tenant_id: str | None,
        tenant_roles: set[str] | None = None,
    ):
        self.user = user
        self.membership = membership
        self.permissions = permissions
        self.tenant_id = tenant_id
        self.tenant_roles = tenant_roles or set()


def resolve_tenant_scope(
    context: RequestContext,
    requested_tenant_id: str | None = None,
    *,
    require_explicit_for_super_admin: bool = False,
    missing_tenant_detail: str = "X-Tenant-ID is required for platform admins",
    cross_tenant_detail: str = "Tenant access denied",
) -> str:
    """Resolve and authorize a tenant scope for tenant-owned operations.

    Non-super-admin users are always locked to their active membership tenant.
    Optional requested_tenant_id must match their membership tenant or a 403 is raised.
    """
    selected_tenant_id = requested_tenant_id or context.tenant_id
    return authorize_action(
        user=context.user,
        tenant_id=selected_tenant_id,
        permission=None,
        membership=context.membership,
        permissions=context.permissions,
        require_membership=True,
        missing_tenant_status=status.HTTP_400_BAD_REQUEST,
        missing_tenant_detail=missing_tenant_detail,
        tenant_mismatch_status=status.HTTP_403_FORBIDDEN,
        tenant_mismatch_detail=cross_tenant_detail,
    )


def ensure_tenant_resource_access(
    *,
    resource_tenant_id: str,
    context: RequestContext,
    not_found_detail: str,
) -> None:
    """Enforce tenant-owned resource visibility for current caller.

    Returns 404 for out-of-scope resources to avoid cross-tenant inference.
    """
    authorize_action(
        user=context.user,
        tenant_id=context.tenant_id,
        permission=None,
        resource=AuthorizationResource(tenant_id=resource_tenant_id),
        membership=context.membership,
        permissions=context.permissions,
        require_membership=True,
        resource_tenant_mismatch_status=status.HTTP_404_NOT_FOUND,
        resource_tenant_mismatch_detail=not_found_detail,
    )



def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication")

    bind_identity(user_id=user.id)
    logger.info("auth_user_resolved", extra={"platform_role": user.platform_role.value})

    return user


def get_request_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> RequestContext:
    memberships = db.scalars(
        select(TenantMembership).where(
            TenantMembership.user_id == current_user.id,
            TenantMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    membership = None

    if current_user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN and not x_tenant_id:
        logger.info("tenant_context_resolved", extra={"scope": "platform", "tenant_id": None})
        return RequestContext(current_user, None, {"*"}, None, tenant_roles={"platform_super_admin"})

    tenant_memberships: list[TenantMembership] = []
    if x_tenant_id:
        tenant_memberships = [m for m in memberships if m.tenant_id == x_tenant_id]
        membership = tenant_memberships[0] if tenant_memberships else None
    elif memberships:
        membership = memberships[0]
        tenant_memberships = [m for m in memberships if m.tenant_id == membership.tenant_id]

    if not membership and current_user.platform_role != PlatformRole.PLATFORM_SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership required")

    if current_user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN:
        if x_tenant_id:
            tenant = db.get(Tenant, x_tenant_id)
            if tenant is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        bind_identity(tenant_id=x_tenant_id)
        logger.info("tenant_context_resolved", extra={"scope": "platform", "tenant_id": x_tenant_id})
        return RequestContext(current_user, membership, {"*"}, x_tenant_id, tenant_roles={"platform_super_admin"})

    assert membership is not None
    permissions: set[str] = set()
    tenant_roles: set[str] = set()
    for tenant_membership in tenant_memberships or [membership]:
        role = db.get(Role, tenant_membership.role_id)
        if role:
            tenant_roles.add(role.name)
            permissions.update(resolve_permissions(role.name, role.permissions))
    overrides = db.scalars(
        select(UserPermissionOverride).where(
            UserPermissionOverride.tenant_id == membership.tenant_id,
            UserPermissionOverride.user_id == current_user.id,
        )
    ).all()
    for override in overrides:
        if override.enabled:
            permissions.add(override.permission)
        else:
            permissions.discard(override.permission)
    bind_identity(tenant_id=membership.tenant_id)
    logger.info(
        "tenant_context_resolved",
        extra={
            "scope": "tenant",
            "tenant_id": membership.tenant_id,
            "role_count": len(tenant_roles),
            "permission_count": len(permissions),
        },
    )
    return RequestContext(current_user, membership, permissions, membership.tenant_id, tenant_roles=tenant_roles)


def require_permissions(*needed: str):
    def dependency(context: RequestContext = Depends(get_request_context)) -> RequestContext:
        for permission in needed:
            authorize_action(
                user=context.user,
                tenant_id=context.tenant_id,
                permission=permission,
                membership=context.membership,
                permissions=context.permissions,
                tenant_roles=context.tenant_roles,
                require_membership=False,
                permission_denied_detail="Insufficient permissions",
            )
        return context

    return dependency
