from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, get_request_context, require_permissions
from app.models import AuditLog, MembershipStatus, Role, TenantMembership, User, UserPermissionOverride
from app.rbac import ALL_KNOWN_PERMISSIONS, ROLE_PERMISSIONS, permission_exists, permissions_csv_for_role, resolve_permissions
from app.schemas import (
    AssignTenantUserRequest,
    TenantUserPermissionsResponse,
    TenantUserSummary,
    UpdateTenantUserPermissionsRequest,
    UserPermissionOverrideItem,
)

router = APIRouter(prefix="/api/tenant-users", tags=["Tenant Users"])


@router.get(
    "/roles/catalog",
    response_model=list[str],
    operation_id="tenant_users_roles_catalog",
    summary="List assignable role catalog",
    description="Returns all standard tenant roles that can be assigned to users.",
    responses={
        200: {"description": "Role catalog returned successfully."},
    },
)
def list_role_catalog(
    context: RequestContext = Depends(require_permissions("admin_read")),
):
    _ = context
    return sorted(role_name for role_name in ROLE_PERMISSIONS if role_name != "platform_super_admin")


@router.get(
    "",
    response_model=list[TenantUserSummary],
    operation_id="tenant_users_list",
    summary="List tenant users",
    description="Lists active users in the current tenant context.",
    responses={
        200: {"description": "Tenant users returned successfully."},
        400: {"description": "X-Tenant-ID is required."},
    },
)
def list_tenant_users(
    context: RequestContext = Depends(require_permissions("admin_read")),
    db: Session = Depends(get_db),
):
    if not context.membership:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")

    memberships = db.scalars(
        select(TenantMembership).where(
            TenantMembership.tenant_id == context.membership.tenant_id,
            TenantMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()

    grouped: dict[str, TenantUserSummary] = {}
    for membership in memberships:
        user = db.get(User, membership.user_id)
        role = db.get(Role, membership.role_id)
        if not user or not role:
            continue
        existing = grouped.get(user.id)
        if existing:
            existing_roles = {item.strip() for item in existing.role_name.split(",") if item.strip()}
            existing_roles.add(role.name)
            existing.role_name = ", ".join(sorted(existing_roles))
            continue
        grouped[user.id] = TenantUserSummary(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
                title=user.title,
                role_name=role.name,
                status=membership.status.value,
            )

    return list(grouped.values())


@router.post(
    "",
    response_model=TenantUserSummary,
    status_code=status.HTTP_201_CREATED,
    operation_id="tenant_users_assign",
    summary="Assign tenant user",
    description="Creates or updates a tenant membership for a user email and role.",
    responses={
        201: {"description": "Tenant user assigned successfully."},
        400: {"description": "X-Tenant-ID is required."},
        403: {"description": "Insufficient permissions."},
        404: {"description": "User or role not found."},
    },
)
def assign_tenant_user(
    payload: AssignTenantUserRequest,
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    if not context.membership:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")

    tenant_id = context.membership.tenant_id
    current_role = db.get(Role, context.membership.role_id)
    has_admin_write = "*" in context.permissions or "admin_write" in context.permissions
    is_owner = current_role is not None and current_role.name == "owner"
    if not has_admin_write and not is_owner:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = db.scalar(
        select(Role).where(
            Role.tenant_id == tenant_id,
            Role.name == payload.role_name,
        )
    )
    if not role:
        if payload.role_name not in ROLE_PERMISSIONS:
            raise HTTPException(status_code=404, detail="Role not found for tenant")
        role = Role(
            tenant_id=tenant_id,
            name=payload.role_name,
            permissions=permissions_csv_for_role(payload.role_name),
            created_by=context.user.id,
        )
        db.add(role)
        db.flush()

    existing = db.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user.id,
            TenantMembership.role_id == role.id,
        )
    )

    if existing:
        existing.status = MembershipStatus.ACTIVE
        membership = existing
        action = "reactivate_membership"
    else:
        membership = TenantMembership(
            tenant_id=tenant_id,
            user_id=user.id,
            role_id=role.id,
            status=MembershipStatus.ACTIVE,
            created_by=context.user.id,
        )
        db.add(membership)
        action = "assign_user"

    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action=action,
            resource_type="tenant_membership",
            resource_id=membership.id,
            details=f"{user.email} -> {role.name}",
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(membership)

    return TenantUserSummary(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        title=user.title,
        role_name=role.name,
        status=membership.status.value,
    )


def _get_memberships_and_user_or_404(db: Session, tenant_id: str, user_id: str) -> tuple[list[TenantMembership], User]:
    memberships = db.scalars(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
            TenantMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    if not memberships:
        raise HTTPException(status_code=404, detail="User is not an active tenant member")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User is not an active tenant member")
    return memberships, user


def _build_permissions_response(db: Session, tenant_id: str, user_id: str) -> TenantUserPermissionsResponse:
    memberships, user = _get_memberships_and_user_or_404(db, tenant_id, user_id)

    role_names: set[str] = set()
    base_permissions: set[str] = set()
    for membership in memberships:
        role = db.get(Role, membership.role_id)
        if not role:
            continue
        role_names.add(role.name)
        base_permissions.update(resolve_permissions(role.name, role.permissions))
    base_permissions.discard("*")
    overrides = db.scalars(
        select(UserPermissionOverride).where(
            UserPermissionOverride.tenant_id == tenant_id,
            UserPermissionOverride.user_id == user_id,
        )
    ).all()

    effective_permissions = set(base_permissions)
    for override in overrides:
        if override.enabled:
            effective_permissions.add(override.permission)
        else:
            effective_permissions.discard(override.permission)

    return TenantUserPermissionsResponse(
        user_id=user.id,
        email=user.email,
        role_name=", ".join(sorted(role_names)),
        base_permissions=sorted(base_permissions),
        effective_permissions=sorted(effective_permissions),
        overrides=[
            UserPermissionOverrideItem(permission=item.permission, enabled=item.enabled)
            for item in sorted(overrides, key=lambda x: x.permission)
        ],
    )


@router.get(
    "/permissions/catalog",
    response_model=list[str],
    operation_id="tenant_users_permissions_catalog",
    summary="List permission catalog",
    description="Returns all function permissions that can be toggled for users.",
    responses={
        200: {"description": "Permission catalog returned successfully."},
        400: {"description": "X-Tenant-ID is required."},
    },
)
def list_permission_catalog(
    context: RequestContext = Depends(require_permissions("admin_read")),
):
    if not context.membership:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")
    return ALL_KNOWN_PERMISSIONS


@router.get(
    "/{user_id}/permissions",
    response_model=TenantUserPermissionsResponse,
    operation_id="tenant_users_permissions_get",
    summary="Get tenant user permissions",
    description="Returns base role permissions plus per-user function overrides.",
    responses={
        200: {"description": "Tenant user permissions returned successfully."},
        400: {"description": "X-Tenant-ID is required."},
        404: {"description": "User is not an active tenant member."},
    },
)
def get_tenant_user_permissions(
    user_id: str,
    context: RequestContext = Depends(require_permissions("admin_read")),
    db: Session = Depends(get_db),
):
    if not context.membership:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")
    return _build_permissions_response(db, context.membership.tenant_id, user_id)


@router.put(
    "/{user_id}/permissions",
    response_model=TenantUserPermissionsResponse,
    operation_id="tenant_users_permissions_update",
    summary="Update tenant user permission overrides",
    description="Sets per-user function toggles for a tenant member.",
    responses={
        200: {"description": "Tenant user permission overrides updated successfully."},
        400: {"description": "Invalid permission values or X-Tenant-ID missing."},
        404: {"description": "User is not an active tenant member."},
    },
)
def update_tenant_user_permissions(
    user_id: str,
    payload: UpdateTenantUserPermissionsRequest,
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    if not context.membership:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")

    tenant_id = context.membership.tenant_id

    current_role = db.get(Role, context.membership.role_id)
    has_admin_write = "*" in context.permissions or "admin_write" in context.permissions
    is_owner = current_role is not None and current_role.name == "owner"
    if not has_admin_write and not is_owner:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    memberships, user = _get_memberships_and_user_or_404(db, tenant_id, user_id)

    invalid = sorted({item.permission for item in payload.overrides if not permission_exists(item.permission)})
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown permissions: {', '.join(invalid)}")

    base_permissions: set[str] = set()
    for membership in memberships:
        role = db.get(Role, membership.role_id)
        if role:
            base_permissions.update(resolve_permissions(role.name, role.permissions))
    existing_overrides = db.scalars(
        select(UserPermissionOverride).where(
            UserPermissionOverride.tenant_id == tenant_id,
            UserPermissionOverride.user_id == user_id,
        )
    ).all()
    existing_by_permission = {item.permission: item for item in existing_overrides}

    for override in payload.overrides:
        desired = override.enabled
        default_enabled = override.permission in base_permissions
        existing = existing_by_permission.get(override.permission)

        # If desired state equals role-default state, remove explicit override.
        if desired == default_enabled:
            if existing:
                db.delete(existing)
            continue

        if existing:
            existing.enabled = desired
        else:
            db.add(
                UserPermissionOverride(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    permission=override.permission,
                    enabled=desired,
                    created_by=context.user.id,
                )
            )

    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="update_user_permission_overrides",
            resource_type="tenant_membership",
            resource_id=user_id,
            details=f"Updated function toggles for {user.email}",
            created_by=context.user.id,
        )
    )
    db.commit()

    return _build_permissions_response(db, tenant_id, user_id)
