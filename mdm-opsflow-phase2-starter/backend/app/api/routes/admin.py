from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import AuditLog, PlatformRole, Project, Role, Tenant, TenantMembership, User
from app.rbac import resolve_permissions

router=APIRouter(prefix="/api/admin",tags=["Platform Administration"])


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.platform_role != PlatformRole.PLATFORM_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Platform super-admin access required")
    return current_user


@router.get("/overview")
def overview(current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    return {
        "platform":"MDM OpsFlow",
        "status":"foundation-ready",
        "role":current_user.platform_role.value,
        "tenants": db.query(Tenant).count(),
        "users": db.query(User).count(),
        "projects": db.query(Project).count(),
    }


@router.get("/tenants/{tenant_id}/users")
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


@router.get("/audit-logs")
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
            "created_at": row.created_at,
            "actor_user_id": row.actor_user_id,
        }
        for row in rows
    ]


@router.get("/permissions-preview")
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
