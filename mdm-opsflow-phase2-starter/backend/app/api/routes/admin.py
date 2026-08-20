from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import (
    AuditLog,
    DocumentExtraction,
    ExtractionIssue,
    IntakeItem,
    IntegrationEvent,
    MembershipStatus,
    PlatformRole,
    Project,
    Role,
    Tenant,
    TenantType,
    TenantMembership,
    Ticket,
    User,
)
from app.rbac import (
    FORMAL_PERMISSION_CATALOG,
    LEGACY_PERMISSION_REQUIREMENTS,
    ROLE_PERMISSION_MATRIX,
    ROLE_PERMISSIONS,
    permissions_csv_for_role,
    resolve_permissions,
)
from app.security import hash_password
from app.services.test_data_cleanup import run_test_data_cleanup
from app.schemas import (
    AdminCreateTenantRequest,
    AdminCreateTenantResponse,
    AdminAssignUserTenantMembershipRequest,
    AdminAuditLogEntry,
    AdminOverviewResponse,
    AdminPermissionsPreviewResponse,
    AdminResetPasswordRequest,
    AdminServiceInsightsResponse,
    AdminDataCountReconciliationResponse,
    AdminDataCountSessionValidation,
    AdminTenantCountDiscrepancyItem,
    AdminTenantCountTriplet,
    AdminTestDataCleanupRequest,
    AdminTestDataCleanupResponse,
    AdminTenantServiceSummaryItem,
    AdminTenantServiceSummaryResponse,
    AdminUpdateUserTenantMembershipRequest,
    AdminTenantUser,
    AdminUserTenantMembershipItem,
    AdminUpdateUserAccessRequest,
    AdminUserAccessItem,
    PermissionCatalogResponse,
)

router = APIRouter(prefix="/api/admin", tags=["Platform Administration"])


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.platform_role != PlatformRole.PLATFORM_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Platform super-admin access required")
    return current_user


def _get_or_create_role(db: Session, tenant_id: str, role_name: str, actor_user_id: str) -> Role:
    if role_name not in ROLE_PERMISSIONS or role_name == "platform_super_admin":
        raise HTTPException(status_code=400, detail="Unknown role")

    role = db.scalar(select(Role).where(Role.tenant_id == tenant_id, Role.name == role_name))
    if role:
        return role

    role = Role(
        tenant_id=tenant_id,
        name=role_name,
        permissions=permissions_csv_for_role(role_name),
        created_by=actor_user_id,
    )
    db.add(role)
    db.flush()
    return role


def _build_membership_item(db: Session, membership: TenantMembership, role: Role | None = None) -> AdminUserTenantMembershipItem:
    tenant = db.get(Tenant, membership.tenant_id)
    resolved_role = role or db.get(Role, membership.role_id)
    return AdminUserTenantMembershipItem(
        membership_id=membership.id,
        user_id=membership.user_id,
        tenant_id=membership.tenant_id,
        tenant_name=tenant.name if tenant else "Unknown",
        role_name=resolved_role.name if resolved_role else "unknown",
        status=membership.status.value,
    )


@router.get(
    "/overview",
    response_model=AdminOverviewResponse,
    operation_id="admin_overview",
    summary="Get platform overview",
    description="Returns platform-level summary metrics for super-admin users.",
    responses={200: {"description": "Overview returned successfully."}, 403: {"description": "Super-admin required."}},
)
def overview(current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(days=7)
    total_tenants = db.scalar(select(func.count()).select_from(Tenant)) or 0
    production_tenants = db.scalar(select(func.count()).select_from(Tenant).where(Tenant.tenant_type == TenantType.PRODUCTION)) or 0
    demo_tenants = db.scalar(select(func.count()).select_from(Tenant).where(Tenant.tenant_type == TenantType.DEMO)) or 0
    test_tenants = db.scalar(select(func.count()).select_from(Tenant).where(Tenant.tenant_type == TenantType.TEST)) or 0
    canary_tenants = db.scalar(select(func.count()).select_from(Tenant).where(Tenant.tenant_type == TenantType.CANARY)) or 0
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    active_users = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
    inactive_users = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(False))) or 0
    total_projects = db.scalar(select(func.count()).select_from(Project)) or 0
    role_count = db.scalar(select(func.count()).select_from(Role)) or 0
    expiring_test_tenants = db.scalar(
        select(func.count()).select_from(Tenant).where(
            Tenant.is_test.is_(True),
            Tenant.expires_at.is_not(None),
            Tenant.expires_at >= now,
            Tenant.expires_at <= threshold,
        )
    ) or 0
    expiring_test_users = db.scalar(
        select(func.count()).select_from(User).where(
            User.is_test.is_(True),
            User.expires_at.is_not(None),
            User.expires_at >= now,
            User.expires_at <= threshold,
        )
    ) or 0

    return {
        "platform":"MDM OpsFlow",
        "status":"foundation-ready",
        "role":current_user.platform_role.value,
        "tenants": total_tenants,
        "production_tenants": production_tenants,
        "demo_tenants": demo_tenants,
        "test_tenants": test_tenants,
        "canary_tenants": canary_tenants,
        "test_and_canary_tenants": test_tenants + canary_tenants,
        "users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "projects": total_projects,
        "role_count": role_count,
        "expiring_test_tenants": expiring_test_tenants,
        "expiring_test_users": expiring_test_users,
    }


@router.get(
    "/tenants/{tenant_id}/users",
    response_model=list[AdminTenantUser],
    operation_id="admin_tenant_users_list",
    summary="List users in tenant",
    description="Returns users who have memberships in the specified tenant.",
    responses={200: {"description": "Tenant users returned successfully."}, 403: {"description": "Super-admin required."}},
)
def tenant_users(tenant_id: str, current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    _ = current_user
    memberships = db.scalars(select(TenantMembership).where(TenantMembership.tenant_id == tenant_id)).all()
    users = []
    for membership in memberships:
        user = db.get(User, membership.user_id)
        if user:
            users.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "title": user.title,
                }
            )
    return users


@router.get(
    "/audit-logs",
    response_model=list[AdminAuditLogEntry],
    operation_id="admin_audit_logs_list",
    summary="List audit logs",
    description="Returns recent audit logs across tenants for super-admin users.",
    responses={200: {"description": "Audit logs returned successfully."}, 403: {"description": "Super-admin required."}},
)
def audit_logs(limit: int = 100, current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    _ = current_user
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "request_id": row.request_id,
            "before_values_json": row.before_values_json,
            "after_values_json": row.after_values_json,
            "occurred_at": row.occurred_at,
            "created_at": row.created_at,
            "actor_user_id": row.actor_user_id,
        }
        for row in rows
    ]


@router.get(
    "/permissions-preview",
    response_model=AdminPermissionsPreviewResponse,
    operation_id="admin_permissions_preview",
    summary="Preview resolved permissions",
    description="Returns effective permissions for selected users and tenant contexts.",
    responses={200: {"description": "Permissions preview returned successfully."}, 403: {"description": "Super-admin required."}},
)
def permissions_preview(
    user_id: str | None = None,
    tenant_id: str | None = None,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _ = current_user

    users_query = select(User)
    if user_id:
        users_query = users_query.where(User.id == user_id)

    users = db.scalars(users_query).all()
    items: list[dict] = []

    for user in users:
        memberships_query = select(TenantMembership).where(TenantMembership.user_id == user.id)
        if tenant_id:
            memberships_query = memberships_query.where(TenantMembership.tenant_id == tenant_id)

        memberships = db.scalars(memberships_query).all()

        if user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN and not memberships:
            items.append(
                {
                    "user_id": user.id,
                    "email": user.email,
                    "platform_role": user.platform_role.value,
                    "tenant_id": None,
                    "role_name": "platform_super_admin",
                    "permissions": ["*"],
                }
            )

        for membership in memberships:
            role = db.get(Role, membership.role_id)
            resolved = sorted(resolve_permissions(role.name, role.permissions) if role else set())
            items.append(
                {
                    "user_id": user.id,
                    "email": user.email,
                    "platform_role": user.platform_role.value,
                    "tenant_id": membership.tenant_id,
                    "role_name": role.name if role else None,
                    "permissions": resolved,
                }
            )

    return {"items": items}


@router.get(
    "/users",
    response_model=list[AdminUserAccessItem],
    operation_id="admin_users_list",
    summary="List platform users",
    description="Returns platform users with access control fields for super-admin management.",
    responses={200: {"description": "Users returned successfully."}, 403: {"description": "Super-admin required."}},
)
def list_users(current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    _ = current_user
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "title": user.title,
            "platform_role": user.platform_role,
            "is_active": user.is_active,
            "user_status": "active" if user.is_active else "inactive",
            "is_test": user.is_test,
            "created_by_automation": user.created_by_automation,
            "test_run_id": user.test_run_id,
            "expires_at": user.expires_at,
        }
        for user in users
    ]


@router.post(
    "/test-data/cleanup",
    response_model=AdminTestDataCleanupResponse,
    operation_id="admin_test_data_cleanup",
    summary="Cleanup expired test data",
    description=(
        "Safely deactivates expired test/canary tenant memberships and test users. "
        "Production and demo tenants are never deleted or deactivated by this process."
    ),
)
def cleanup_test_data(
    payload: AdminTestDataCleanupRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _ = current_user
    report = run_test_data_cleanup(db, dry_run=payload.dry_run)
    return AdminTestDataCleanupResponse(
        dry_run=report.dry_run,
        executed_at=report.executed_at,
        eligible_tenants=report.eligible_tenants,
        eligible_users=report.eligible_users,
        deactivated_memberships=report.deactivated_memberships,
        deactivated_users=report.deactivated_users,
        preserved_audit_logs=report.preserved_audit_logs,
        tenant_actions=[
            {
                "tenant_id": item.tenant_id,
                "tenant_name": item.tenant_name,
                "tenant_type": item.tenant_type,
                "is_test": item.is_test,
                "created_by_automation": item.created_by_automation,
                "test_run_id": item.test_run_id,
                "expires_at": item.expires_at,
                "memberships_to_deactivate": item.memberships_to_deactivate,
            }
            for item in report.tenant_actions
        ],
        user_actions=[
            {
                "user_id": item.user_id,
                "email": item.email,
                "is_test": item.is_test,
                "created_by_automation": item.created_by_automation,
                "test_run_id": item.test_run_id,
                "expires_at": item.expires_at,
                "memberships_to_deactivate": item.memberships_to_deactivate,
            }
            for item in report.user_actions
        ],
    )


@router.delete(
    "/users/{user_id}",
    response_model=AdminUserAccessItem,
    operation_id="admin_user_delete",
    summary="Delete user",
    description="Deactivates a user and all tenant memberships as a super-admin safety action without hard-deleting their audit history.",
    responses={
        200: {"description": "User deactivated successfully."},
        400: {"description": "Self-deletion or invalid action."},
        403: {"description": "Super-admin required."},
        404: {"description": "User not found."},
    },
)
def delete_user(
    user_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own super-admin account")

    user.is_active = False
    user.refresh_token_hash = None
    user.refresh_token_expires_at = None

    memberships = db.scalars(select(TenantMembership).where(TenantMembership.user_id == user.id)).all()
    for membership in memberships:
        membership.status = MembershipStatus.INACTIVE

    if memberships:
        tenant_id_for_audit = memberships[0].tenant_id
        db.add(
            AuditLog(
                tenant_id=tenant_id_for_audit,
                actor_user_id=current_user.id,
                action="admin_delete_user",
                resource_type="user",
                resource_id=user.id,
                details=f"Deactivated user {user.email} and {len(memberships)} tenant memberships",
                created_by=current_user.id,
            )
        )

    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "title": user.title,
        "platform_role": user.platform_role,
        "is_active": user.is_active,
        "user_status": "active" if user.is_active else "inactive",
        "is_test": user.is_test,
        "created_by_automation": user.created_by_automation,
        "test_run_id": user.test_run_id,
        "expires_at": user.expires_at,
    }


@router.get(
    "/roles/catalog",
    response_model=list[str],
    operation_id="admin_roles_catalog",
    summary="List assignable tenant roles",
    description="Returns all standard tenant roles that super-admin can assign.",
    responses={200: {"description": "Roles returned successfully."}, 403: {"description": "Super-admin required."}},
)
def admin_roles_catalog(current_user: User = Depends(require_super_admin)):
    _ = current_user
    return sorted(role_name for role_name in ROLE_PERMISSIONS if role_name != "platform_super_admin")


@router.get(
    "/permissions/formal-catalog",
    response_model=PermissionCatalogResponse,
    operation_id="admin_permissions_formal_catalog",
    summary="Get formal permission catalog",
    description="Returns granular permission definitions, role matrix, and legacy aliases for platform governance.",
)
def admin_formal_permission_catalog(current_user: User = Depends(require_super_admin)):
    _ = current_user
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


@router.post(
    "/tenants",
    response_model=AdminCreateTenantResponse,
    status_code=201,
    operation_id="admin_tenant_create",
    summary="Create tenant",
    description="Creates a tenant workspace and seeds standard tenant roles.",
    responses={200: {"description": "Tenant created successfully."}, 403: {"description": "Super-admin required."}},
)
def create_tenant(
    payload: AdminCreateTenantRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    normalized_name = payload.tenant_name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Tenant name is required")

    existing = db.scalar(select(Tenant).where(Tenant.name == normalized_name))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Tenant name already exists")

    tenant = Tenant(
        name=normalized_name,
        company_type=payload.company_type.strip(),
        tenant_type=payload.tenant_type,
        is_test=payload.is_test,
        created_by_automation=payload.created_by_automation,
        test_run_id=payload.test_run_id,
        expires_at=payload.expires_at,
        preferred_language=payload.preferred_language.strip() or "en",
        selected_modules=",".join(item.strip() for item in payload.selected_modules if item.strip()),
    )
    db.add(tenant)
    db.flush()

    for role_name in ROLE_PERMISSIONS:
        if role_name == "platform_super_admin":
            continue
        db.add(
            Role(
                tenant_id=tenant.id,
                name=role_name,
                permissions=permissions_csv_for_role(role_name),
                created_by=current_user.id,
            )
        )

    db.add(
        AuditLog(
            tenant_id=tenant.id,
            actor_user_id=current_user.id,
            action="admin_create_tenant",
            resource_type="tenant",
            resource_id=tenant.id,
            details=f"Created tenant {tenant.name}",
            created_by=current_user.id,
        )
    )

    db.commit()
    db.refresh(tenant)
    return AdminCreateTenantResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tenant_type=tenant.tenant_type,
        is_test=tenant.is_test,
        created_by_automation=tenant.created_by_automation,
        test_run_id=tenant.test_run_id,
        expires_at=tenant.expires_at,
    )


@router.get(
    "/users/{user_id}/memberships",
    response_model=list[AdminUserTenantMembershipItem],
    operation_id="admin_user_memberships_list",
    summary="List user tenant memberships",
    description="Returns tenant memberships and assigned roles for a platform user.",
)
def list_user_memberships(user_id: str, current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    _ = current_user
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    memberships = db.scalars(
        select(TenantMembership).where(TenantMembership.user_id == user_id).order_by(TenantMembership.created_at.asc())
    ).all()
    return [_build_membership_item(db, membership) for membership in memberships]


@router.post(
    "/users/{user_id}/memberships",
    response_model=AdminUserTenantMembershipItem,
    status_code=201,
    operation_id="admin_user_membership_assign",
    summary="Assign tenant role to user",
    description="Adds or reactivates a tenant membership role for a user.",
)
def assign_user_membership(
    user_id: str,
    payload: AdminAssignUserTenantMembershipRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tenant = db.get(Tenant, payload.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    role = _get_or_create_role(db, payload.tenant_id, payload.role_name, current_user.id)
    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == payload.tenant_id,
            TenantMembership.role_id == role.id,
        )
    )
    if membership:
        membership.status = MembershipStatus.ACTIVE
        action = "admin_reactivate_user_membership"
    else:
        membership = TenantMembership(
            tenant_id=payload.tenant_id,
            user_id=user_id,
            role_id=role.id,
            status=MembershipStatus.ACTIVE,
            created_by=current_user.id,
        )
        db.add(membership)
        db.flush()
        action = "admin_assign_user_membership"

    if current_user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN:
        membership.status = MembershipStatus.ACTIVE
        action = "super_admin_create_active_membership"

    if not user.is_active:
        user.is_active = True

    db.add(
        AuditLog(
            tenant_id=payload.tenant_id,
            actor_user_id=current_user.id,
            action=action,
            resource_type="tenant_membership",
            resource_id=membership.id,
            details=f"{user.email} -> {role.name}",
            created_by=current_user.id,
        )
    )
    db.commit()
    db.refresh(membership)
    return _build_membership_item(db, membership, role)


@router.patch(
    "/users/{user_id}/memberships/{membership_id}",
    response_model=AdminUserTenantMembershipItem,
    operation_id="admin_user_membership_update",
    summary="Remap tenant membership",
    description="Moves or updates a user's tenant role membership, including status changes.",
)
def update_user_membership(
    user_id: str,
    membership_id: str,
    payload: AdminUpdateUserTenantMembershipRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    membership = db.scalar(select(TenantMembership).where(TenantMembership.id == membership_id, TenantMembership.user_id == user_id))
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    current_role = db.get(Role, membership.role_id)
    target_tenant_id = payload.tenant_id or membership.tenant_id
    tenant = db.get(Tenant, target_tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    target_role_name = payload.role_name or (current_role.name if current_role else "")
    target_role = _get_or_create_role(db, target_tenant_id, target_role_name, current_user.id)

    duplicate = db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == target_tenant_id,
            TenantMembership.role_id == target_role.id,
            TenantMembership.id != membership.id,
        )
    )
    if duplicate is not None:
        duplicate.status = MembershipStatus(payload.status) if payload.status else MembershipStatus.ACTIVE
        membership.status = MembershipStatus.INACTIVE
        target_membership = duplicate
    else:
        membership.tenant_id = target_tenant_id
        membership.role_id = target_role.id
        if payload.status:
            membership.status = MembershipStatus(payload.status)
        target_membership = membership

    if target_membership.status == MembershipStatus.ACTIVE and not user.is_active:
        user.is_active = True

    db.add(
        AuditLog(
            tenant_id=target_tenant_id,
            actor_user_id=current_user.id,
            action="admin_update_user_membership",
            resource_type="tenant_membership",
            resource_id=target_membership.id,
            details=f"{user.email} -> {target_role.name} ({target_membership.status.value})",
            created_by=current_user.id,
        )
    )
    db.commit()
    db.refresh(target_membership)
    return _build_membership_item(db, target_membership, target_role)


@router.patch(
    "/users/{user_id}/access",
    response_model=AdminUserAccessItem,
    operation_id="admin_user_access_update",
    summary="Update platform user access",
    description="Updates platform role and active status for a user.",
    responses={
        200: {"description": "User access updated successfully."},
        403: {"description": "Super-admin required."},
        404: {"description": "User not found."},
    },
)
def update_user_access(
    user_id: str,
    payload: AdminUpdateUserAccessRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent accidental lockout by blocking self-demotion/deactivation.
    if user.id == current_user.id:
        if payload.platform_role and payload.platform_role != PlatformRole.PLATFORM_SUPER_ADMIN:
            raise HTTPException(status_code=400, detail="Cannot remove your own super-admin access")
        if payload.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    changed_fields: list[str] = []
    if payload.platform_role is not None and user.platform_role != payload.platform_role:
        user.platform_role = payload.platform_role
        changed_fields.append(f"platform_role={payload.platform_role.value}")

    if payload.is_active is not None and user.is_active != payload.is_active:
        user.is_active = payload.is_active
        changed_fields.append(f"is_active={payload.is_active}")
        if payload.is_active is False:
            # Immediate session revocation for inactive accounts.
            user.refresh_token_hash = None
            user.refresh_token_expires_at = None
            changed_fields.append("refresh_tokens_revoked=true")

    if changed_fields:
        memberships = db.scalars(select(TenantMembership).where(TenantMembership.user_id == user.id)).all()
        tenant_id_for_audit = memberships[0].tenant_id if memberships else None
        if tenant_id_for_audit:
            db.add(
                AuditLog(
                    tenant_id=tenant_id_for_audit,
                    actor_user_id=current_user.id,
                    action="admin_update_user_access",
                    resource_type="user",
                    resource_id=user.id,
                    details=f"{user.email}: {', '.join(changed_fields)}",
                    created_by=current_user.id,
                )
            )

    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "title": user.title,
        "platform_role": user.platform_role,
        "is_active": user.is_active,
        "user_status": "active" if user.is_active else "inactive",
        "is_test": user.is_test,
        "created_by_automation": user.created_by_automation,
        "test_run_id": user.test_run_id,
        "expires_at": user.expires_at,
    }


@router.post(
    "/users/{user_id}/reset-password",
    response_model=AdminUserAccessItem,
    operation_id="admin_user_password_reset",
    summary="Reset user password",
    description="Resets a user's password as a platform super-admin operation.",
    responses={
        200: {"description": "Password reset successfully."},
        403: {"description": "Super-admin required."},
        404: {"description": "User not found."},
    },
)
def reset_user_password(
    user_id: str,
    payload: AdminResetPasswordRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    user.refresh_token_hash = None
    user.refresh_token_expires_at = None

    memberships = db.scalars(select(TenantMembership).where(TenantMembership.user_id == user.id)).all()
    tenant_id_for_audit = memberships[0].tenant_id if memberships else None
    if tenant_id_for_audit:
        db.add(
            AuditLog(
                tenant_id=tenant_id_for_audit,
                actor_user_id=current_user.id,
                action="admin_reset_password",
                resource_type="user",
                resource_id=user.id,
                details=f"Password reset for {user.email}",
                created_by=current_user.id,
            )
        )

    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "title": user.title,
        "platform_role": user.platform_role,
        "is_active": user.is_active,
        "user_status": "active" if user.is_active else "inactive",
        "is_test": user.is_test,
        "created_by_automation": user.created_by_automation,
        "test_run_id": user.test_run_id,
        "expires_at": user.expires_at,
    }


@router.get(
    "/tenant-service-summary",
    response_model=AdminTenantServiceSummaryResponse,
    operation_id="admin_tenant_service_summary",
    summary="Get tenant service summary",
    description="Returns per-tenant usage summaries across core platform services.",
    responses={200: {"description": "Tenant service summary returned successfully."}, 403: {"description": "Super-admin required."}},
)
def tenant_service_summary(current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    _ = current_user
    tenant_type_filter: TenantType | None = None
    tenant_status_filter = "all"
    tenants = db.scalars(select(Tenant).order_by(Tenant.name.asc())).all()
    return _tenant_service_summary_impl(db, tenants, tenant_type_filter, tenant_status_filter)


@router.get(
    "/tenant-service-summary/filter",
    response_model=AdminTenantServiceSummaryResponse,
    operation_id="admin_tenant_service_summary_filtered",
    summary="Get filtered tenant service summary",
    description="Returns per-tenant summaries filtered by tenant type and user status.",
)
def tenant_service_summary_filtered(
    tenant_type: TenantType | None = None,
    status: str = "all",
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _ = current_user
    normalized_status = status.strip().lower()
    if normalized_status not in {"all", "active", "inactive"}:
        raise HTTPException(status_code=400, detail="status must be one of: all, active, inactive")

    tenants_query = select(Tenant).order_by(Tenant.name.asc())
    if tenant_type is not None:
        tenants_query = tenants_query.where(Tenant.tenant_type == tenant_type)
    tenants = db.scalars(tenants_query).all()
    return _tenant_service_summary_impl(db, tenants, tenant_type, normalized_status)


def _tenant_service_summary_impl(
    db: Session,
    tenants: list[Tenant],
    tenant_type_filter: TenantType | None,
    tenant_status_filter: str,
) -> AdminTenantServiceSummaryResponse:
    items: list[AdminTenantServiceSummaryItem] = []

    for tenant in tenants:
        memberships = db.scalars(select(TenantMembership).where(TenantMembership.tenant_id == tenant.id)).all()
        user_ids = [membership.user_id for membership in memberships]
        active_users_count = 0
        inactive_users_count = 0
        if user_ids:
            active_users_count = db.scalar(
                select(func.count()).select_from(User).where(User.id.in_(user_ids), User.is_active.is_(True))
            ) or 0
            inactive_users_count = db.scalar(
                select(func.count()).select_from(User).where(User.id.in_(user_ids), User.is_active.is_(False))
            ) or 0

        users_count = active_users_count + inactive_users_count
        if tenant_status_filter == "active":
            users_count = active_users_count
        elif tenant_status_filter == "inactive":
            users_count = inactive_users_count

        projects_count = db.scalar(select(func.count()).select_from(Project).where(Project.tenant_id == tenant.id)) or 0
        tickets_count = db.scalar(select(func.count()).select_from(Ticket).where(Ticket.tenant_id == tenant.id)) or 0
        intake_count = db.scalar(select(func.count()).select_from(IntakeItem).where(IntakeItem.tenant_id == tenant.id)) or 0
        extraction_count = db.scalar(select(func.count()).select_from(DocumentExtraction).where(DocumentExtraction.tenant_id == tenant.id)) or 0
        pending_reviews = db.scalar(
            select(func.count()).select_from(DocumentExtraction).where(
                DocumentExtraction.tenant_id == tenant.id,
                DocumentExtraction.status.in_(["review_pending", "review_submitted"]),
            )
        ) or 0

        items.append(
            AdminTenantServiceSummaryItem(
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                tenant_type=tenant.tenant_type,
                tenant_status_filter=tenant_status_filter,
                is_test=tenant.is_test,
                created_by_automation=tenant.created_by_automation,
                test_run_id=tenant.test_run_id,
                expires_at=tenant.expires_at,
                users=users_count,
                active_users=active_users_count,
                inactive_users=inactive_users_count,
                projects=projects_count,
                tickets=tickets_count,
                intake_items=intake_count,
                extractions=extraction_count,
                pending_reviews=pending_reviews,
            )
        )

    return AdminTenantServiceSummaryResponse(
        tenant_type_filter=tenant_type_filter,
        tenant_status_filter=tenant_status_filter,
        items=items,
    )


@router.get(
    "/service-insights",
    response_model=AdminServiceInsightsResponse,
    operation_id="admin_service_insights",
    summary="Get platform service insights",
    description="Returns platform-wide service KPIs and improvement opportunities for super-admin users.",
    responses={200: {"description": "Service insights returned successfully."}, 403: {"description": "Super-admin required."}},
)
def service_insights(current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    _ = current_user
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(days=7)

    tenants = db.scalar(select(func.count()).select_from(Tenant)) or 0
    users = db.scalar(select(func.count()).select_from(User)) or 0
    active_users = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
    inactive_users = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(False))) or 0
    projects = db.scalar(select(func.count()).select_from(Project)) or 0
    tickets = db.scalar(select(func.count()).select_from(Ticket)) or 0
    production_tenants = db.scalar(select(func.count()).select_from(Tenant).where(Tenant.tenant_type == TenantType.PRODUCTION)) or 0
    demo_tenants = db.scalar(select(func.count()).select_from(Tenant).where(Tenant.tenant_type == TenantType.DEMO)) or 0
    test_tenants = db.scalar(select(func.count()).select_from(Tenant).where(Tenant.tenant_type == TenantType.TEST)) or 0
    canary_tenants = db.scalar(select(func.count()).select_from(Tenant).where(Tenant.tenant_type == TenantType.CANARY)) or 0
    role_count = db.scalar(select(func.count()).select_from(Role)) or 0
    expiring_test_tenants = db.scalar(
        select(func.count()).select_from(Tenant).where(
            Tenant.is_test.is_(True),
            Tenant.expires_at.is_not(None),
            Tenant.expires_at >= now,
            Tenant.expires_at <= threshold,
        )
    ) or 0
    expiring_test_users = db.scalar(
        select(func.count()).select_from(User).where(
            User.is_test.is_(True),
            User.expires_at.is_not(None),
            User.expires_at >= now,
            User.expires_at <= threshold,
        )
    ) or 0
    intake_items = db.scalar(select(func.count()).select_from(IntakeItem)) or 0
    intake_needs_review = db.scalar(select(func.count()).select_from(IntakeItem).where(IntakeItem.needs_review.is_(True))) or 0

    extractions_pending_review = db.scalar(
        select(func.count()).select_from(DocumentExtraction).where(DocumentExtraction.status == "review_pending")
    ) or 0
    extractions_review_submitted = db.scalar(
        select(func.count()).select_from(DocumentExtraction).where(DocumentExtraction.status == "review_submitted")
    ) or 0

    unresolved_extraction_issues = db.scalar(
        select(func.count()).select_from(ExtractionIssue).where(ExtractionIssue.resolved.is_(False))
    ) or 0

    integration_events_pending = db.scalar(
        select(func.count()).select_from(IntegrationEvent).where(IntegrationEvent.status == "pending")
    ) or 0
    integration_events_failed = db.scalar(
        select(func.count()).select_from(IntegrationEvent).where(IntegrationEvent.status.in_(["failed", "dead_lettered"]))
    ) or 0

    opportunities: list[str] = []
    if intake_needs_review > 0:
        opportunities.append("Reduce intake review backlog by resolving pending intake items.")
    if extractions_pending_review + extractions_review_submitted > 0:
        opportunities.append("Speed up extraction approvals to unblock downstream ticket and billing workflows.")
    if unresolved_extraction_issues > 0:
        opportunities.append("Address unresolved extraction issues to improve data quality and automation confidence.")
    if integration_events_failed > 0:
        opportunities.append("Resolve failed/dead-letter integration events to improve service reliability.")
    if integration_events_pending > 25:
        opportunities.append("Investigate integration queue throughput; pending events are accumulating.")
    if not opportunities:
        opportunities.append("No major platform bottlenecks detected right now.")

    return AdminServiceInsightsResponse(
        tenants=tenants,
        users=users,
        active_users=active_users,
        inactive_users=inactive_users,
        projects=projects,
        tickets=tickets,
        production_tenants=production_tenants,
        demo_tenants=demo_tenants,
        test_tenants=test_tenants,
        canary_tenants=canary_tenants,
        test_and_canary_tenants=test_tenants + canary_tenants,
        role_count=role_count,
        expiring_test_tenants=expiring_test_tenants,
        expiring_test_users=expiring_test_users,
        customer_growth_tenants=production_tenants,
        intake_items=intake_items,
        intake_needs_review=intake_needs_review,
        extractions_pending_review=extractions_pending_review,
        extractions_review_submitted=extractions_review_submitted,
        unresolved_extraction_issues=unresolved_extraction_issues,
        integration_events_pending=integration_events_pending,
        integration_events_failed=integration_events_failed,
        opportunities=opportunities,
    )


def _reported_tenant_counts(db: Session, tenant_id: str) -> AdminTenantCountTriplet:
    return AdminTenantCountTriplet(
        users=db.scalar(select(func.count()).select_from(TenantMembership).where(TenantMembership.tenant_id == tenant_id)) or 0,
        projects=db.scalar(select(func.count()).select_from(Project).where(Project.tenant_id == tenant_id)) or 0,
        tickets=db.scalar(select(func.count()).select_from(Ticket).where(Ticket.tenant_id == tenant_id)) or 0,
    )


def _authoritative_tenant_counts(db: Session, tenant_id: str) -> AdminTenantCountTriplet:
    # Authoritative source is the normalized domain tables for memberships/projects/tickets.
    return AdminTenantCountTriplet(
        users=db.scalar(select(func.count()).select_from(TenantMembership).where(TenantMembership.tenant_id == tenant_id)) or 0,
        projects=db.scalar(select(func.count()).select_from(Project).where(Project.tenant_id == tenant_id)) or 0,
        tickets=db.scalar(select(func.count()).select_from(Ticket).where(Ticket.tenant_id == tenant_id)) or 0,
    )


@router.get(
    "/diagnostics/data-count-reconciliation",
    response_model=AdminDataCountReconciliationResponse,
    operation_id="admin_data_count_reconciliation",
    summary="Reconcile tenant dashboard counts",
    description=(
        "Compares expected (displayed/stored) tenant counters against authoritative table counts. "
        "Discrepancies are flagged and never auto-corrected."
    ),
)
def reconcile_data_counts(
    tenant_id: str | None = None,
    expected_total_tenants: int | None = None,
    expected_total_users: int | None = None,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _ = current_user

    tenants_query = select(Tenant).order_by(Tenant.name.asc())
    if tenant_id:
        tenants_query = tenants_query.where(Tenant.id == tenant_id)
    tenants = db.scalars(tenants_query).all()

    items: list[AdminTenantCountDiscrepancyItem] = []
    mismatched_tenants = 0

    for tenant in tenants:
        expected = _reported_tenant_counts(db, tenant.id)
        actual = _authoritative_tenant_counts(db, tenant.id)

        discrepancies: list[str] = []
        if expected.users != actual.users:
            discrepancies.append(f"users expected={expected.users} actual={actual.users}")
        if expected.projects != actual.projects:
            discrepancies.append(f"projects expected={expected.projects} actual={actual.projects}")
        if expected.tickets != actual.tickets:
            discrepancies.append(f"tickets expected={expected.tickets} actual={actual.tickets}")

        is_reconciled = len(discrepancies) == 0
        if not is_reconciled:
            mismatched_tenants += 1

        items.append(
            AdminTenantCountDiscrepancyItem(
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                expected=expected,
                actual=actual,
                discrepancies=discrepancies,
                is_reconciled=is_reconciled,
            )
        )

    actual_total_tenants = db.scalar(select(func.count()).select_from(Tenant)) or 0
    actual_total_users = db.scalar(select(func.count()).select_from(User)) or 0

    session_discrepancies: list[str] = []
    if expected_total_tenants is not None and expected_total_tenants != actual_total_tenants:
        session_discrepancies.append(
            f"total_tenants expected={expected_total_tenants} actual={actual_total_tenants}"
        )
    if expected_total_users is not None and expected_total_users != actual_total_users:
        session_discrepancies.append(
            f"total_users expected={expected_total_users} actual={actual_total_users}"
        )

    return AdminDataCountReconciliationResponse(
        generated_at=datetime.now(timezone.utc),
        total_tenants=len(tenants),
        mismatched_tenants=mismatched_tenants,
        items=items,
        session_validation=AdminDataCountSessionValidation(
            expected_total_tenants=expected_total_tenants,
            actual_total_tenants=actual_total_tenants,
            expected_total_users=expected_total_users,
            actual_total_users=actual_total_users,
            discrepancies=session_discrepancies,
        ),
    )
