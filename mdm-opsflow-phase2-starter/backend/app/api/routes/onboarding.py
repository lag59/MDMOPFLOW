from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import AuditLog, MembershipStatus, Project, ProjectStatus, Role, Tenant, TenantMembership, User
from app.rbac import permissions_csv_for_role
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


@router.get("/company-types")
def company_types():
    return sorted(COMPANY_TYPES)


@router.post("/complete", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
def complete_onboarding(
    payload: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.company_type not in COMPANY_TYPES:
        raise HTTPException(status_code=400, detail="Invalid company type")

    has_membership = db.scalar(select(TenantMembership).where(TenantMembership.user_id == current_user.id))
    if has_membership:
        raise HTTPException(status_code=400, detail="User has already completed onboarding")

    tenant = Tenant(
        name=payload.company_name,
        company_type=payload.company_type,
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
    return OnboardingResponse(tenant_id=tenant.id, project_id=first_project.id)
