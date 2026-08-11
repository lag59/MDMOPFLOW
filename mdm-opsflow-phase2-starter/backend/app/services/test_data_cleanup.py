from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import MembershipStatus, PlatformRole, Tenant, TenantMembership, TenantType, User


@dataclass
class TenantCleanupAction:
    tenant_id: str
    tenant_name: str
    tenant_type: TenantType
    is_test: bool
    created_by_automation: bool
    test_run_id: str | None
    expires_at: datetime | None
    memberships_to_deactivate: int


@dataclass
class UserCleanupAction:
    user_id: str
    email: str
    is_test: bool
    created_by_automation: bool
    test_run_id: str | None
    expires_at: datetime | None
    memberships_to_deactivate: int


@dataclass
class CleanupReport:
    dry_run: bool
    executed_at: datetime
    eligible_tenants: int
    eligible_users: int
    deactivated_memberships: int
    deactivated_users: int
    preserved_audit_logs: bool
    tenant_actions: list[TenantCleanupAction]
    user_actions: list[UserCleanupAction]


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def run_test_data_cleanup(db: Session, dry_run: bool = True) -> CleanupReport:
    now_utc = datetime.now(timezone.utc)

    eligible_tenants = db.scalars(
        select(Tenant).where(
            and_(
                Tenant.expires_at.is_not(None),
                Tenant.expires_at <= now_utc,
                or_(
                    Tenant.is_test.is_(True),
                    Tenant.tenant_type.in_([TenantType.TEST, TenantType.CANARY]),
                ),
                Tenant.tenant_type.notin_([TenantType.PRODUCTION, TenantType.DEMO]),
            )
        )
    ).all()

    tenant_actions: list[TenantCleanupAction] = []
    user_membership_deactivations: dict[str, int] = {}
    deactivated_memberships = 0

    for tenant in eligible_tenants:
        active_memberships = db.scalars(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant.id,
                TenantMembership.status == MembershipStatus.ACTIVE,
            )
        ).all()

        tenant_actions.append(
            TenantCleanupAction(
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                tenant_type=tenant.tenant_type,
                is_test=tenant.is_test,
                created_by_automation=tenant.created_by_automation,
                test_run_id=tenant.test_run_id,
                expires_at=tenant.expires_at,
                memberships_to_deactivate=len(active_memberships),
            )
        )

        for membership in active_memberships:
            deactivated_memberships += 1
            user_membership_deactivations[membership.user_id] = user_membership_deactivations.get(membership.user_id, 0) + 1
            if not dry_run:
                membership.status = MembershipStatus.INACTIVE

    user_actions: list[UserCleanupAction] = []
    deactivated_users = 0

    candidate_users = db.scalars(
        select(User).where(
            and_(
                User.expires_at.is_not(None),
                User.expires_at <= now_utc,
                User.is_test.is_(True),
            )
        )
    ).all()

    for user in candidate_users:
        if user.platform_role == PlatformRole.PLATFORM_SUPER_ADMIN:
            continue

        active_memberships = db.scalars(
            select(TenantMembership).where(
                TenantMembership.user_id == user.id,
                TenantMembership.status == MembershipStatus.ACTIVE,
            )
        ).all()

        safe_to_deactivate = True
        for membership in active_memberships:
            tenant = db.get(Tenant, membership.tenant_id)
            if tenant is None:
                continue
            if tenant.tenant_type in {TenantType.PRODUCTION, TenantType.DEMO}:
                safe_to_deactivate = False
                break

        if not safe_to_deactivate:
            continue

        user_actions.append(
            UserCleanupAction(
                user_id=user.id,
                email=user.email,
                is_test=user.is_test,
                created_by_automation=user.created_by_automation,
                test_run_id=user.test_run_id,
                expires_at=user.expires_at,
                memberships_to_deactivate=user_membership_deactivations.get(user.id, 0),
            )
        )

        if user.is_active:
            deactivated_users += 1
        if not dry_run:
            user.is_active = False
            user.refresh_token_hash = None
            user.refresh_token_expires_at = None

    if not dry_run:
        db.commit()

    return CleanupReport(
        dry_run=dry_run,
        executed_at=now_utc,
        eligible_tenants=len(tenant_actions),
        eligible_users=len(user_actions),
        deactivated_memberships=deactivated_memberships,
        deactivated_users=deactivated_users,
        preserved_audit_logs=True,
        tenant_actions=tenant_actions,
        user_actions=user_actions,
    )
