from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, get_request_context, require_permissions
from app.models import AuditLog, MembershipStatus, Role, TenantMembership, User
from app.schemas import AssignTenantUserRequest, TenantUserSummary

router = APIRouter(prefix="/api/tenant-users", tags=["Tenant Users"])


@router.get("", response_model=list[TenantUserSummary])
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

    items: list[TenantUserSummary] = []
    for membership in memberships:
        user = db.get(User, membership.user_id)
        role = db.get(Role, membership.role_id)
        if not user or not role:
            continue
        items.append(
            TenantUserSummary(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
                title=user.title,
                role_name=role.name,
                status=membership.status.value,
            )
        )

    return items


@router.post("", response_model=TenantUserSummary, status_code=status.HTTP_201_CREATED)
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
        raise HTTPException(status_code=404, detail="Role not found for tenant")

    existing = db.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user.id,
        )
    )

    if existing:
        existing.role_id = role.id
        existing.status = MembershipStatus.ACTIVE
        membership = existing
        action = "update_membership"
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
