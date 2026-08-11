from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import AuditLog, MembershipStatus, Project, ProjectStatus, Role, Tenant, TenantMembership, User
from app.rbac import ROLE_PERMISSIONS, permissions_csv_for_role
from app.schemas import OnboardingRequest, OnboardingResponse

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])

COMPANY_TYPES = {
    "Earthwork / Site Development",
    "General Contractor",
    "Trucking / Hauling",
    "Heavy Civil",
    "Safety / Training",
    "Specialty Contractor",
    "Other",
}


@router.get(
    "/company-types",
    operation_id="onboarding_company_types",
    summary="List company types",
    description="Returns the supported company types for onboarding selection.",
    responses={
        200: {"description": "Company types returned successfully."},
    },
)
def company_types():
    return sorted(COMPANY_TYPES)


@router.post(
    "/complete",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="onboarding_complete",
    summary="Complete onboarding",
    description=(
        "Creates tenant, owner role, owner membership (company admin), and first project for the "
        "authenticated user. "
        "Can only be completed once per user."
    ),
    responses={
        201: {"description": "Onboarding completed successfully."},
        400: {"description": "Invalid company type or onboarding already completed."},
        401: {"description": "Authentication required."},
    },
)
def complete_onboarding(
    payload: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invalid_company_types = [item for item in payload.company_types if item not in COMPANY_TYPES]
    if invalid_company_types:
        raise HTTPException(status_code=400, detail="Invalid company type")

    has_membership = db.scalar(select(TenantMembership).where(TenantMembership.user_id == current_user.id))
    if has_membership:
        raise HTTPException(status_code=400, detail="User has already completed onboarding")

    tenant = Tenant(
        name=payload.company_name,
        company_type=",".join(payload.company_types),
        tenant_type=payload.tenant_type,
        is_test=payload.is_test,
        created_by_automation=payload.created_by_automation,
        test_run_id=payload.test_run_id,
        expires_at=payload.expires_at,
        preferred_language=payload.language,
        selected_modules=",".join(payload.modules),
    )
    db.add(tenant)
    db.flush()

    owner_role = Role(
        tenant_id=tenant.id,
        name="owner",
        permissions=permissions_csv_for_role("owner"),
        created_by=current_user.id,
    )
    db.add(owner_role)
    db.flush()

    # Seed standard tenant roles at onboarding so role lists are complete from day one.
    for role_name in ROLE_PERMISSIONS:
        if role_name in {"platform_super_admin", "owner"}:
            continue
        db.add(
            Role(
                tenant_id=tenant.id,
                name=role_name,
                permissions=permissions_csv_for_role(role_name),
                created_by=current_user.id,
            )
        )

    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=current_user.id,
        role_id=owner_role.id,
        status=MembershipStatus.ACTIVE,
        created_by=current_user.id,
    )
    db.add(membership)

    first_project = Project(
        tenant_id=tenant.id,
        project_name=payload.first_project_name,
        project_number="PRJ-001",
        customer="",
        address="",
        project_manager=current_user.display_name,
        status=ProjectStatus.PLANNING,
        description="Created during onboarding",
        created_by=current_user.id,
    )
    db.add(first_project)
    db.flush()

    for invited_email in payload.invite_emails:
        log = AuditLog(
            tenant_id=tenant.id,
            actor_user_id=current_user.id,
            action="invite_member",
            resource_type="user",
            resource_id=invited_email,
            details="Invitation queued",
            created_by=current_user.id,
        )
        db.add(log)

    db.add(
        AuditLog(
            tenant_id=tenant.id,
            actor_user_id=current_user.id,
            action="complete_onboarding",
            resource_type="tenant",
            resource_id=tenant.id,
            details=f"Modules={tenant.selected_modules}",
            created_by=current_user.id,
        )
    )

    db.commit()
    return OnboardingResponse(
        tenant_id=tenant.id,
        project_id=first_project.id,
        tenant_type=tenant.tenant_type,
        is_test=tenant.is_test,
        created_by_automation=tenant.created_by_automation,
        test_run_id=tenant.test_run_id,
        expires_at=tenant.expires_at,
    )
