from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PlatformRole, Role, TenantMembership, User
from app.rbac import resolve_permissions
from app.security import TokenError, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class RequestContext:
    def __init__(self, user: User, membership: TenantMembership | None, permissions: set[str]):
        self.user = user
        self.membership = membership
        self.permissions = permissions



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

    return user


def get_request_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> RequestContext:
    memberships = db.scalars(select(TenantMembership).where(TenantMembership.user_id == current_user.id)).all()
    membership = None

    if current_user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN and not x_tenant_id:
        return RequestContext(current_user, None, {"*"})

    if x_tenant_id:
        membership = next((m for m in memberships if m.tenant_id == x_tenant_id), None)
    elif memberships:
        membership = memberships[0]

    if not membership and current_user.platform_role != PlatformRole.PLATFORM_SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership required")

    if current_user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN:
        return RequestContext(current_user, membership, {"*"})

    role = db.get(Role, membership.role_id)
    permissions = resolve_permissions(role.name, role.permissions) if role else set()
    return RequestContext(current_user, membership, permissions)


def require_permissions(*needed: str):
    def dependency(context: RequestContext = Depends(get_request_context)) -> RequestContext:
        if "*" in context.permissions:
            return context
        missing = [name for name in needed if name not in context.permissions]
        if missing:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return context

    return dependency
