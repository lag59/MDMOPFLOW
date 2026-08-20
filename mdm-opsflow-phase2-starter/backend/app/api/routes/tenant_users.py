from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import add_audit_log, get_request_id
from app.db import get_db
from app.dependencies import RequestContext, get_request_context, require_permissions
from app.models import MembershipStatus, PlatformRole, Role, TenantMembership, User, UserPermissionOverride
from app.rbac import (
    ALL_KNOWN_PERMISSIONS,
    FORMAL_PERMISSION_CATALOG,
    LEGACY_PERMISSION_REQUIREMENTS,
    ROLE_PERMISSION_MATRIX,
    ROLE_PERMISSIONS,
    permission_exists,
    permissions_csv_for_role,
    resolve_permissions,
)
from app.security import hash_password
from app.schemas import (
    AssignTenantUserRequest,
    PermissionCatalogResponse,
    TenantUserResetPasswordRequest,
    TenantUserPermissionsResponse,
    TenantUserSummary,
    UpdateTenantUserMembershipRequest,
    UpdateTenantUserPermissionsRequest,
    UserPermissionOverrideItem,
)

router = APIRouter(prefix="/api/tenant-users", tags=["Tenant Users"])

ADMINISTRATIVE_ROLES = {"tenant_admin", "administrator"}
ADMIN_GRADE_PERMISSIONS = {
    "admin_read",
    "admin_write",
    "user.view",
    "user.manage",
    "membership.assign",
}


def _tenant_id_from_context_or_400(context: RequestContext) -> str:
    tenant_id = context.membership.tenant_id if context.membership else context.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")
    return tenant_id


def _actor_role(context: RequestContext, db: Session) -> str | None:
    if context.membership is None:
        return None
    role = db.get(Role, context.membership.role_id)
    return role.name if role else None


def _ensure_owner_cannot_grant_admin_role(*, actor_role_name: str | None, target_role_name: str) -> None:
    if actor_role_name == "owner" and target_role_name in ADMINISTRATIVE_ROLES:
        raise HTTPException(status_code=403, detail="Owner role cannot grant administrative tenant roles")


def _ensure_owner_cannot_grant_admin_permissions(*, actor_role_name: str | None, overrides: list[UserPermissionOverrideItem]) -> None:
    if actor_role_name != "owner":
        return
    blocked = sorted({item.permission for item in overrides if item.permission in ADMIN_GRADE_PERMISSIONS})
    if blocked:
        raise HTTPException(
            status_code=403,
            detail=f"Owner role cannot grant administrative permissions: {', '.join(blocked)}",
        )


def _ensure_can_manage_tenant_users(context: RequestContext, db: Session) -> str | None:
    actor_role_name = _actor_role(context, db)
    is_platform_super_admin = context.user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN
    is_tenant_admin = actor_role_name == "tenant_admin"
    is_owner = actor_role_name == "owner"
    if not is_platform_super_admin and not is_tenant_admin and not is_owner:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return actor_role_name


def _tenant_user_summary(db: Session, user: User, memberships: list[TenantMembership]) -> TenantUserSummary:
    role_names: set[str] = set()
    statuses = {membership.status for membership in memberships}
    for membership in memberships:
        role = db.get(Role, membership.role_id)
        if role:
            role_names.add(role.name)

    if MembershipStatus.ACTIVE in statuses:
        status_value = MembershipStatus.ACTIVE.value
    elif MembershipStatus.INVITED in statuses:
        status_value = MembershipStatus.INVITED.value
    else:
        status_value = MembershipStatus.INACTIVE.value

    return TenantUserSummary(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        title=user.title,
        role_name=", ".join(sorted(role_names)),
        status=status_value,
    )


def _get_any_tenant_memberships_and_user_or_404(db: Session, tenant_id: str, user_id: str) -> tuple[list[TenantMembership], User]:
    memberships = db.scalars(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
        )
    ).all()
    if not memberships:
        raise HTTPException(status_code=404, detail="User is not a tenant member")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User is not a tenant member")
    return memberships, user


def _get_or_create_role(db: Session, tenant_id: str, role_name: str, actor_user_id: str) -> Role:
    role = db.scalar(select(Role).where(Role.tenant_id == tenant_id, Role.name == role_name))
    if role:
        return role
    if role_name not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=404, detail="Role not found for tenant")
    role = Role(
        tenant_id=tenant_id,
        name=role_name,
        permissions=permissions_csv_for_role(role_name),
        created_by=actor_user_id,
    )
    db.add(role)
    db.flush()
    return role


def _ensure_tenant_keeps_active_owner(db: Session, tenant_id: str, target_user_id: str) -> None:
    active_memberships = db.scalars(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    active_owner_user_ids: set[str] = set()
    for membership in active_memberships:
        role = db.get(Role, membership.role_id)
        if role and role.name == "owner":
            active_owner_user_ids.add(membership.user_id)

    if target_user_id in active_owner_user_ids and len(active_owner_user_ids) == 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last active owner membership for this tenant")


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
    tenant_id = _tenant_id_from_context_or_400(context)

    memberships = db.scalars(select(TenantMembership).where(TenantMembership.tenant_id == tenant_id)).all()

    grouped: dict[str, list[TenantMembership]] = {}
    for membership in memberships:
        user = db.get(User, membership.user_id)
        if not user:
            continue
        grouped.setdefault(user.id, []).append(membership)

    return [_tenant_user_summary(db, db.get(User, user_id), user_memberships) for user_id, user_memberships in grouped.items() if db.get(User, user_id)]


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
    request: Request,
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context_or_400(context)
    actor_role_name = _ensure_can_manage_tenant_users(context, db)
    is_platform_super_admin = context.user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN
    _ensure_owner_cannot_grant_admin_role(actor_role_name=actor_role_name, target_role_name=payload.role_name)

    normalized_email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if not user:
        existing_case_variant = db.scalar(select(User).where(User.email.ilike(normalized_email)))
        if existing_case_variant is not None:
            existing_case_variant.email = normalized_email
            user = existing_case_variant
        else:
            inferred_display_name = payload.display_name.strip() or normalized_email.split("@")[0].replace(".", " ").replace("_", " ").title()
            user = User(
                email=normalized_email,
                password_hash=hash_password(payload.temporary_password),
                display_name=inferred_display_name,
                title=payload.title.strip(),
                platform_role=PlatformRole.USER,
                is_active=True,
            )
            db.add(user)
            db.flush()

    role = _get_or_create_role(db, tenant_id, payload.role_name, context.user.id)

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

    if is_platform_super_admin:
        membership.status = MembershipStatus.ACTIVE
        action = "super_admin_create_active_membership"

    # Membership activation should also enable the account for tenant access.
    if not user.is_active:
        user.is_active = True

    db.flush()
    add_audit_log(
        db,
        actor_user_id=context.user.id,
        action=action,
        entity_type="tenant_membership",
        entity_id=membership.id,
        tenant_id=tenant_id,
        request_id=get_request_id(request),
        details=f"{user.email} -> {role.name}",
        after={
            "user_id": user.id,
            "email": user.email,
            "role": role.name,
            "membership_status": membership.status.value,
        },
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


@router.patch(
    "/{user_id}/membership",
    response_model=TenantUserSummary,
    operation_id="tenant_users_membership_update",
    summary="Update tenant user membership",
    description="Updates a tenant user's role or membership status within the current tenant context.",
    responses={
        200: {"description": "Tenant user membership updated successfully."},
        400: {"description": "X-Tenant-ID is required or tenant would lose its owner."},
        403: {"description": "Insufficient permissions."},
        404: {"description": "User is not a tenant member."},
    },
)
def update_tenant_user_membership(
    user_id: str,
    payload: UpdateTenantUserMembershipRequest,
    request: Request,
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context_or_400(context)
    actor_role_name = _ensure_can_manage_tenant_users(context, db)
    memberships, user = _get_any_tenant_memberships_and_user_or_404(db, tenant_id, user_id)

    requested_status = MembershipStatus(payload.status) if payload.status else None
    if requested_status == MembershipStatus.INACTIVE:
        _ensure_tenant_keeps_active_owner(db, tenant_id, user_id)
    if payload.role_name:
        _ensure_owner_cannot_grant_admin_role(actor_role_name=actor_role_name, target_role_name=payload.role_name)
        changing_last_owner = payload.role_name != "owner" and any(
            (db.get(Role, membership.role_id) and db.get(Role, membership.role_id).name == "owner" and membership.status == MembershipStatus.ACTIVE)
            for membership in memberships
        )
        if changing_last_owner:
            _ensure_tenant_keeps_active_owner(db, tenant_id, user_id)

    before = {
        "roles": [db.get(Role, membership.role_id).name for membership in memberships if db.get(Role, membership.role_id)],
        "statuses": [membership.status.value for membership in memberships],
    }

    if requested_status == MembershipStatus.INACTIVE:
        for membership in memberships:
            membership.status = MembershipStatus.INACTIVE
    elif payload.role_name:
        target_role = _get_or_create_role(db, tenant_id, payload.role_name, context.user.id)
        target_membership = next((membership for membership in memberships if membership.role_id == target_role.id), None)
        if target_membership is None:
            target_membership = TenantMembership(
                tenant_id=tenant_id,
                user_id=user.id,
                role_id=target_role.id,
                status=MembershipStatus.ACTIVE,
                created_by=context.user.id,
            )
            db.add(target_membership)
            memberships.append(target_membership)
        for membership in memberships:
            membership.status = MembershipStatus.ACTIVE if membership.role_id == target_role.id else MembershipStatus.INACTIVE
    elif requested_status is not None:
        for membership in memberships:
            membership.status = requested_status

    if requested_status == MembershipStatus.ACTIVE and not user.is_active:
        user.is_active = True

    db.flush()
    after_memberships, _ = _get_any_tenant_memberships_and_user_or_404(db, tenant_id, user_id)
    after = {
        "roles": [db.get(Role, membership.role_id).name for membership in after_memberships if db.get(Role, membership.role_id)],
        "statuses": [membership.status.value for membership in after_memberships],
    }
    add_audit_log(
        db,
        actor_user_id=context.user.id,
        action="update_tenant_user_membership",
        entity_type="tenant_membership",
        entity_id=user.id,
        tenant_id=tenant_id,
        request_id=get_request_id(request),
        details=f"Updated tenant membership for {user.email}",
        before=before,
        after=after,
    )
    db.commit()
    return _tenant_user_summary(db, user, after_memberships)


@router.post(
    "/{user_id}/reset-password",
    response_model=TenantUserSummary,
    operation_id="tenant_users_password_reset",
    summary="Reset tenant user password",
    description="Resets a staff user's password within the current tenant context.",
    responses={
        200: {"description": "Password reset successfully."},
        400: {"description": "X-Tenant-ID is required."},
        403: {"description": "Insufficient permissions."},
        404: {"description": "User is not a tenant member."},
    },
)
def reset_tenant_user_password(
    user_id: str,
    payload: TenantUserResetPasswordRequest,
    request: Request,
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context_or_400(context)
    _ensure_can_manage_tenant_users(context, db)
    memberships, user = _get_any_tenant_memberships_and_user_or_404(db, tenant_id, user_id)

    if user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN and context.user.platform_role != PlatformRole.PLATFORM_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only platform super-admin can reset another super-admin password")

    user.password_hash = hash_password(payload.new_password)
    user.refresh_token_hash = None
    user.refresh_token_expires_at = None
    add_audit_log(
        db,
        actor_user_id=context.user.id,
        action="reset_tenant_user_password",
        entity_type="user",
        entity_id=user.id,
        tenant_id=tenant_id,
        request_id=get_request_id(request),
        details=f"Password reset for {user.email}",
    )
    db.commit()
    return _tenant_user_summary(db, user, memberships)


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
    _tenant_id_from_context_or_400(context)
    return ALL_KNOWN_PERMISSIONS


@router.get(
    "/permissions/formal-catalog",
    response_model=PermissionCatalogResponse,
    operation_id="tenant_users_permissions_formal_catalog",
    summary="Get formal permission catalog and role matrix",
    description="Returns granular permission definitions, role matrix, and legacy aliases.",
)
def get_formal_permission_catalog(
    context: RequestContext = Depends(require_permissions("admin_read")),
):
    _tenant_id_from_context_or_400(context)
    return PermissionCatalogResponse(
        permissions=FORMAL_PERMISSION_CATALOG,
        role_matrix={
            role_name: permissions
            for role_name, permissions in ROLE_PERMISSION_MATRIX.items()
            if role_name != "platform_super_admin"
        },
        legacy_aliases={
            key: sorted(value)
            for key, value in LEGACY_PERMISSION_REQUIREMENTS.items()
        },
    )


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
    tenant_id = _tenant_id_from_context_or_400(context)
    return _build_permissions_response(db, tenant_id, user_id)


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
    request: Request,
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context_or_400(context)

    actor_role_name = _actor_role(context, db)
    is_platform_super_admin = context.user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN
    is_tenant_admin = actor_role_name == "tenant_admin"
    is_owner = actor_role_name == "owner"
    if not is_platform_super_admin and not is_tenant_admin and not is_owner:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    _ensure_owner_cannot_grant_admin_permissions(actor_role_name=actor_role_name, overrides=payload.overrides)

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
    before_overrides = {item.permission: item.enabled for item in existing_overrides}

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
    refreshed_overrides = db.scalars(
        select(UserPermissionOverride).where(
            UserPermissionOverride.tenant_id == tenant_id,
            UserPermissionOverride.user_id == user_id,
        )
    ).all()
    after_overrides = {item.permission: item.enabled for item in refreshed_overrides}
    add_audit_log(
        db,
        actor_user_id=context.user.id,
        action="update_user_permission_overrides",
        entity_type="tenant_membership",
        entity_id=user_id,
        tenant_id=tenant_id,
        request_id=get_request_id(request),
        details=f"Updated function toggles for {user.email}",
        before={"overrides": before_overrides},
        after={"overrides": after_overrides},
    )
    db.commit()

    return _build_permissions_response(db, tenant_id, user_id)
