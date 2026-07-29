from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import IntakeItem, Project
from app.schemas import (
    CustomerPortalBillingStatusResponse,
    CustomerPortalDocumentStatusResponse,
    CustomerPortalProjectSummaryResponse,
)
from app.services.project_costing import ProjectCostAggregation

router = APIRouter(prefix="/api/customer-portal", tags=["Customer Portal"])


def _require_tenant(context: RequestContext) -> str:
    tenant_id = context.membership.tenant_id if context.membership else context.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")
    return tenant_id


def _get_project_or_404(db: Session, tenant_id: str, project_id: str) -> Project:
    item = db.get(Project, project_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return item


@router.get(
    "/projects",
    response_model=list[CustomerPortalProjectSummaryResponse],
    operation_id="customer_portal_projects_list",
    summary="List customer portal projects",
)
def list_customer_projects(
    context: RequestContext = Depends(require_permissions("portal_customer_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    projects = db.scalars(select(Project).where(Project.tenant_id == tenant_id).order_by(Project.project_name.asc())).all()

    items: list[CustomerPortalProjectSummaryResponse] = []
    for project in projects:
        profitability = ProjectCostAggregation.get_project_profitability(db, project.id)
        document_totals = db.execute(
            select(
                func.count(IntakeItem.id),
                func.sum(case((IntakeItem.needs_review == True, 1), else_=0)),
            ).where(
                IntakeItem.tenant_id == tenant_id,
                IntakeItem.project_id == project.id,
            )
        ).one()
        total_documents = int(document_totals[0] or 0)
        pending_documents = int(document_totals[1] or 0)
        items.append(
            CustomerPortalProjectSummaryResponse(
                project_id=project.id,
                project_name=project.project_name,
                project_number=project.project_number,
                status=project.status.value if hasattr(project.status, "value") else str(project.status),
                project_manager=project.project_manager,
                actual_revenue=profitability["actual_revenue"],
                ticket_count=profitability["ticket_count"],
                total_documents=total_documents,
                pending_review_documents=pending_documents,
            )
        )

    return items


@router.get(
    "/projects/{project_id}/billing-status",
    response_model=CustomerPortalBillingStatusResponse,
    operation_id="customer_portal_billing_status_get",
    summary="Get customer portal billing status",
)
def get_customer_billing_status(
    project_id: str,
    context: RequestContext = Depends(require_permissions("portal_customer_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    project = _get_project_or_404(db, tenant_id, project_id)
    profitability = ProjectCostAggregation.get_project_profitability(db, project.id)
    return CustomerPortalBillingStatusResponse(
        project_id=project.id,
        project_name=project.project_name,
        status=project.status.value if hasattr(project.status, "value") else str(project.status),
        actual_revenue=profitability["actual_revenue"],
        ticket_count=profitability["ticket_count"],
        total_tons=profitability["total_tons"],
        total_cubic_yards=profitability["total_cubic_yards"],
        revenue_shortfall=profitability["revenue_shortfall"],
    )


@router.get(
    "/projects/{project_id}/documents",
    response_model=CustomerPortalDocumentStatusResponse,
    operation_id="customer_portal_documents_get",
    summary="Get customer portal document status",
)
def get_customer_document_status(
    project_id: str,
    context: RequestContext = Depends(require_permissions("portal_customer_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    project = _get_project_or_404(db, tenant_id, project_id)

    totals = db.execute(
        select(
            func.count(IntakeItem.id),
            func.sum(case((IntakeItem.needs_review == True, 1), else_=0)),
            func.max(IntakeItem.created_at),
        ).where(
            IntakeItem.tenant_id == tenant_id,
            IntakeItem.project_id == project.id,
        )
    ).one()

    return CustomerPortalDocumentStatusResponse(
        project_id=project.id,
        project_name=project.project_name,
        total_documents=int(totals[0] or 0),
        pending_review_documents=int(totals[1] or 0),
        latest_document_at=totals[2],
    )
