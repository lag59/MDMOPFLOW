from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import Ticket
from app.schemas import TicketCreate, TicketResponse, TicketUpdate


router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


def _tenant_id_from_context(context: RequestContext) -> str:
    if context.tenant_id:
        return context.tenant_id
    if context.membership:
        return context.membership.tenant_id
    raise HTTPException(status_code=400, detail="X-Tenant-ID is required for platform admins")


@router.get(
    "",
    response_model=list[TicketResponse],
    operation_id="tickets_list",
    summary="List tickets",
)
def list_tickets(
    tenant_id: str | None = Query(default=None),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    if "*" in context.permissions:
        if tenant_id:
            return db.scalars(select(Ticket).where(Ticket.tenant_id == tenant_id)).all()
        return db.scalars(select(Ticket)).all()

    assert context.membership is not None
    return db.scalars(select(Ticket).where(Ticket.tenant_id == context.membership.tenant_id)).all()


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="tickets_create",
    summary="Create ticket",
)
def create_ticket(
    payload: TicketCreate,
    context: RequestContext = Depends(require_permissions("intake_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)

    ticket = Ticket(
        tenant_id=tenant_id,
        intake_item_id=payload.intake_item_id,
        project_id=payload.project_id,
        ticket_number=payload.ticket_number,
        truck=payload.truck,
        driver=payload.driver,
        material=payload.material,
        origin=payload.origin,
        destination=payload.destination,
        load_time=payload.load_time,
        unload_time=payload.unload_time,
        miles=payload.miles,
        weight=payload.weight,
        volume_yards=payload.volume_yards,
        tons=payload.tons,
        fuel_cost=payload.fuel_cost,
        revenue=payload.revenue,
        status=payload.status,
        notes=payload.notes,
        created_by=context.user.id,
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    operation_id="tickets_get",
    summary="Get ticket",
)
def get_ticket(
    ticket_id: str,
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if "*" not in context.permissions and (
        not context.membership or ticket.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    operation_id="tickets_update",
    summary="Update ticket",
)
def update_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    context: RequestContext = Depends(require_permissions("intake_write")),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if "*" not in context.permissions and (
        not context.membership or ticket.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Ticket not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, key, value)

    db.commit()
    db.refresh(ticket)
    return ticket
