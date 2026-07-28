"""
Billing API routes

Handles invoice generation and billing operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import Project
from app.schemas import InvoiceGenerationRequest, InvoiceResponse
from app.services.billing import BillingService

router = APIRouter(prefix="/api/invoices", tags=["Billing & Invoices"])


@router.post(
    "/generate",
    response_model=InvoiceResponse,
    operation_id="invoices_generate",
    summary="Generate invoice",
    description="Generates an invoice for a project from all approved tickets using configured rates.",
    responses={
        200: {"description": "Invoice generated successfully."},
        404: {"description": "Project not found in caller scope."},
    },
)
def generate_invoice(
    project_id: str,
    payload: InvoiceGenerationRequest,
    context: RequestContext = Depends(require_permissions("billing_write")),
    db: Session = Depends(get_db),
):
    """
    Generate an invoice for a project.
    
    Rates are applied in priority order:
    1. rate_per_ton (if ticket has tons)
    2. rate_per_yard (if ticket has cubic yards)
    3. rate_per_load (flat per ticket)
    4. Falls back to ticket.revenue field
    
    Only includes tickets with status matching status_filter (default: "approved").
    """
    # Verify project exists and is accessible
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if "*" not in context.permissions and (
        not context.membership or project.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        invoice_data = BillingService.generate_invoice_line_items(
            db,
            project_id,
            rate_per_ton=payload.rate_per_ton,
            rate_per_yard=payload.rate_per_yard,
            rate_per_load=payload.rate_per_load,
            status_filter=payload.status_filter,
        )
        return InvoiceResponse(**invoice_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/estimate",
    response_model=float,
    operation_id="invoices_estimate",
    summary="Estimate invoice total",
    description="Quick estimate of invoice total without generating full line items.",
    responses={
        200: {"description": "Invoice estimate returned."},
        404: {"description": "Project not found in caller scope."},
    },
)
def estimate_invoice(
    project_id: str,
    payload: InvoiceGenerationRequest,
    context: RequestContext = Depends(require_permissions("billing_read")),
    db: Session = Depends(get_db),
):
    """
    Get a quick estimate of the invoice total.
    
    Useful for dashboard preview before generating full invoice.
    """
    # Verify project exists and is accessible
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if "*" not in context.permissions and (
        not context.membership or project.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        total = BillingService.estimate_invoice_amount(
            db,
            project_id,
            rate_per_ton=payload.rate_per_ton,
            rate_per_yard=payload.rate_per_yard,
            rate_per_load=payload.rate_per_load,
        )
        return float(total)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
