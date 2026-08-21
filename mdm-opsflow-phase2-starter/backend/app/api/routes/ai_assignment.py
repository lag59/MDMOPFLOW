"""
API routes for AI-powered ticket assignment.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, get_request_context, require_permissions
from app.models import Ticket
from app.schemas import AIWorkflowRouteRequest, AIWorkflowRouteResponse, TicketResponse
from app.services.ai_routing import route_input_to_workflows
from app.services.ai_ticket_assignment import AITicketAssignment

router = APIRouter(prefix="/api/ai", tags=["AI & Automation"])


@router.post("/workflow/route", response_model=AIWorkflowRouteResponse, summary="Route a single note into customer, material, and report workflows")
def route_workflow_input(
    payload: AIWorkflowRouteRequest,
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> AIWorkflowRouteResponse:
    tenant_id = context.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")
    return route_input_to_workflows(
        db,
        tenant_id=tenant_id,
        actor_user_id=context.user.id,
        payload=payload,
    )


@router.post("/tickets/auto-assign")
def auto_assign_tickets(
    confidence_threshold: float = Query(0.75, ge=0.5, le=1.0),
    context: RequestContext = Depends(require_permissions("ai_assignment_write")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Automatically assign unassigned tickets to projects based on location matching.
    
    Uses AI fuzzy matching to find the best project for each unassigned ticket by comparing
    the ticket destination with project addresses.
    
    Query parameters:
    - confidence_threshold: Minimum confidence score (0.5-1.0) for auto-assignment. Default 0.75.
      Lower values assign more tickets, higher values are more conservative.
    
    Returns assignment statistics and details.
    """
    tenant_id = context.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    # Run auto-assignment
    result = AITicketAssignment.auto_assign_unassigned_tickets(
        db=db,
        tenant_id=tenant_id,
        confidence_threshold=confidence_threshold,
    )
    
    return result


@router.get("/tickets/{ticket_id}/project-suggestions")
def get_project_suggestions(
    ticket_id: str,
    top_n: int = Query(5, ge=1, le=20),
    context: RequestContext = Depends(require_permissions("ai_assignment_read")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    Get ranked project suggestions for a ticket based on location matching.
    
    Returns the top N projects that could match this ticket's destination location,
    sorted by confidence score (highest first).
    
    Path parameters:
    - ticket_id: ID of the ticket to get suggestions for
    
    Query parameters:
    - top_n: Number of suggestions to return (1-20). Default 5.
    
    Returns list of suggested projects with confidence scores and match reasons.
    """
    tenant_id = context.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    # Verify ticket exists and belongs to tenant
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.tenant_id == tenant_id,
    ).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get suggestions
    suggestions = AITicketAssignment.get_project_suggestions_for_ticket(
        db=db,
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        top_n=top_n,
    )
    
    return suggestions


@router.post("/tickets/{ticket_id}/assign-to-project/{project_id}")
def assign_ticket_to_project(
    ticket_id: str,
    project_id: str,
    context: RequestContext = Depends(require_permissions("ai_assignment_write")),
    db: Session = Depends(get_db),
) -> TicketResponse:
    """
    Assign a ticket to a specific project.
    
    This endpoint is used to apply a suggested project assignment (from AI suggestions)
    or to manually assign a ticket to a project.
    
    Path parameters:
    - ticket_id: ID of the ticket to assign
    - project_id: ID of the project to assign the ticket to
    
    Returns the updated ticket.
    """
    tenant_id = context.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    # Verify ticket exists and belongs to tenant
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.tenant_id == tenant_id,
    ).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Verify project exists and belongs to tenant
    from app.models import Project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.tenant_id == tenant_id,
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Assign ticket to project
    ticket.project_id = project_id
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    return TicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        truck=ticket.truck,
        driver=ticket.driver,
        material=ticket.material,
        origin=ticket.origin,
        destination=ticket.destination,
        load_time=ticket.load_time,
        unload_time=ticket.unload_time,
        miles=ticket.miles,
        weight=ticket.weight,
        volume_yards=ticket.volume_yards,
        tons=ticket.tons,
        fuel_cost=ticket.fuel_cost,
        revenue=ticket.revenue,
        status=ticket.status,
        notes=ticket.notes,
        project_id=ticket.project_id,
    )
