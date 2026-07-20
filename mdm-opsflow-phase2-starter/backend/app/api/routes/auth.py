from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Role, Tenant, TenantMembership, User
from app.schemas import AuthLoginRequest, AuthRegisterRequest, AuthResponse, MeMembership, MeResponse, RefreshRequest, TokenPair
from app.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


ACCESS_TOKEN_MINUTES = 30
REFRESH_TOKEN_MINUTES = 60 * 24 * 14


def _make_auth_response(user: User, tenant_id: str | None) -> AuthResponse:
    access_token = create_token(
        {
            "sub": user.id,
            "role": user.platform_role.value,
            "tenant_id": tenant_id,
        },
        expires_minutes=ACCESS_TOKEN_MINUTES,
    )
    refresh_token = create_token({"sub": user.id, "type": "refresh"}, expires_minutes=REFRESH_TOKEN_MINUTES)
    user.refresh_token_hash = hash_password(refresh_token)
    user.refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_MINUTES)

    return AuthResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        title=user.title,
        platform_role=user.platform_role,
        tenant_id=tenant_id,
        tokens=TokenPair(access_token=access_token, refresh_token=refresh_token),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        title="",
    )
    db.add(user)
    db.flush()

    result = _make_auth_response(user, tenant_id=None)
    db.commit()
    db.refresh(user)
    return result


@router.post("/login", response_model=AuthResponse)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    tenant_id = payload.tenant_id
    if not tenant_id:
        membership = db.scalar(select(TenantMembership).where(TenantMembership.user_id == user.id))
        tenant_id = membership.tenant_id if membership else None

    response = _make_auth_response(user, tenant_id=tenant_id)
    db.commit()
    db.refresh(user)
    return response


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = db.scalars(select(TenantMembership).where(TenantMembership.user_id == current_user.id)).all()

    membership_data: list[MeMembership] = []
    for membership in memberships:
        tenant = db.get(Tenant, membership.tenant_id)
        role_name = "member"
        if membership.role_id:
            role = db.get(Role, membership.role_id)
            role_name = role.name if role else "member"
        membership_data.append(
            MeMembership(
                tenant_id=membership.tenant_id,
                tenant_name=tenant.name if tenant else "Unknown",
                role_name=role_name,
            )
        )

    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        title=current_user.title,
        platform_role=current_user.platform_role,
        memberships=membership_data,
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    from app.security import TokenError, decode_token

    try:
        data = decode_token(payload.refresh_token)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.get(User, data.get("sub"))
    if not user or not user.refresh_token_hash or not verify_password(payload.refresh_token, user.refresh_token_hash):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    expires_at = user.refresh_token_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    access_token = create_token({"sub": user.id, "role": user.platform_role.value}, expires_minutes=ACCESS_TOKEN_MINUTES)
    new_refresh = create_token({"sub": user.id, "type": "refresh"}, expires_minutes=REFRESH_TOKEN_MINUTES)
    user.refresh_token_hash = hash_password(new_refresh)
    user.refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_MINUTES)
    db.commit()
    return TokenPair(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.refresh_token_hash = None
    current_user.refresh_token_expires_at = None
    db.commit()
    return None
