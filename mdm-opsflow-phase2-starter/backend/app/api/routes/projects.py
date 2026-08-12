from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import add_audit_log, get_request_id
from app.authorization import AuthorizationResource, authorize_action
from app.db import get_db
from app.dependencies import RequestContext, ensure_tenant_resource_access, require_permissions, resolve_tenant_scope
from app.models import Project, Ticket
from app.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectCostResponse,
    ProjectProfitabilityResponse,
    TicketResponse,
)
from app.services.project_costing import ProjectCostAggregation

router = APIRouter(prefix="/api/projects", tags=["Projects"])


def _ensure_project_access(project: Project, context: RequestContext) -> None:
    """Authorize access to a loaded project.

    Platform super admins can access a specific project without first selecting
    a tenant because the project itself carries the tenant scope.
    """
    if "*" in context.permissions and not context.tenant_id:
        return

    authorize_action(
        user=context.user,
        tenant_id=context.tenant_id,
        permission=None,
        resource=AuthorizationResource(tenant_id=project.tenant_id),
        membership=context.membership,
        permissions=context.permissions,
        tenant_roles=context.tenant_roles,
        require_membership=True,
        resource_tenant_mismatch_status=status.HTTP_404_NOT_FOUND,
        resource_tenant_mismatch_detail="Project not found",
    )


@router.get(
    "",
    response_model=list[ProjectResponse],
    operation_id="projects_list",
    summary="List projects",
    description=(
        "Returns projects visible to the caller. Tenant users are scoped to their tenant. "
        "Platform admins may pass tenant_id to scope the list."
    ),
    responses={
        200: {"description": "Projects returned successfully."},
    },
)
def list_projects(
    tenant_id: str | None = None,
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    if "*" in context.permissions:
        if tenant_id:
            return db.scalars(select(Project).where(Project.tenant_id == tenant_id)).all()
        return db.scalars(select(Project)).all()

    scoped_tenant_id = resolve_tenant_scope(context, tenant_id)
    return db.scalars(select(Project).where(Project.tenant_id == scoped_tenant_id)).all()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="projects_create",
    summary="Create project",
    description="Creates a project in the current tenant context.",
    responses={
        201: {"description": "Project created successfully."},
        400: {"description": "X-Tenant-ID missing for platform admin write."},
        403: {"description": "Tenant membership required."},
    },
)
def create_project(
    payload: ProjectCreate,
    request: Request,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    tenant_id = resolve_tenant_scope(context)

    item = Project(
        tenant_id=tenant_id,
        project_name=payload.project_name,
        project_number=payload.project_number,
        customer=payload.customer,
        address=payload.address,
        project_manager=payload.project_manager,
        start_date=payload.start_date,
        end_date=payload.end_date,
        contract_amount=payload.contract_amount,
        budget=payload.budget,
        status=payload.status,
        description=payload.description,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    add_audit_log(
        db,
        actor_user_id=context.user.id,
        action="create_project",
        entity_type="project",
        entity_id=item.id,
        tenant_id=item.tenant_id,
        request_id=get_request_id(request),
        details=item.project_name,
        after={
            "project_name": item.project_name,
            "project_number": item.project_number,
            "status": item.status.value,
        },
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    operation_id="projects_get",
    summary="Get project",
    description="Returns a single project if it exists and is visible in caller scope.",
    responses={
        200: {"description": "Project returned successfully."},
        404: {"description": "Project not found in caller scope."},
    },
)
def get_project(
    project_id: str,
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_project_access(item, context)
    return item


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    operation_id="projects_update",
    summary="Update project",
    description="Applies partial updates to a project in caller scope.",
    responses={
        200: {"description": "Project updated successfully."},
        404: {"description": "Project not found in caller scope."},
    },
)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    request: Request,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_project_access(item, context)

    before = {
        "project_name": item.project_name,
        "project_number": item.project_number,
        "status": item.status.value,
        "description": item.description,
    }
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    add_audit_log(
        db,
        actor_user_id=context.user.id,
        action="update_project",
        entity_type="project",
        entity_id=item.id,
        tenant_id=item.tenant_id,
        request_id=get_request_id(request),
        details="Updated project",
        before=before,
        after={
            "project_name": item.project_name,
            "project_number": item.project_number,
            "status": item.status.value,
            "description": item.description,
        },
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="projects_delete",
    summary="Delete project",
    description="Deletes a project in caller scope.",
    responses={
        204: {"description": "Project deleted successfully."},
        404: {"description": "Project not found in caller scope."},
    },
)
def delete_project(
    project_id: str,
    request: Request,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_project_access(item, context)

    add_audit_log(
        db,
        actor_user_id=context.user.id,
        action="delete_project",
        entity_type="project",
        entity_id=item.id,
        tenant_id=item.tenant_id,
        request_id=get_request_id(request),
        details=item.project_name,
        before={
            "project_name": item.project_name,
            "project_number": item.project_number,
            "status": item.status.value,
        },
    )
    db.delete(item)
    db.commit()
    return None


@router.get(
    "/{project_id}/costs",
    response_model=ProjectCostResponse,
    operation_id="projects_costs",
    summary="Get project costs",
    description="Returns aggregated costs from all approved/completed tickets in a project.",
    responses={
        200: {"description": "Project costs returned successfully."},
        404: {"description": "Project not found in caller scope."},
    },
)
def get_project_costs(
    project_id: str,
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    # Verify project exists and is accessible
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_project_access(item, context)

    costs = ProjectCostAggregation.get_project_costs(db, project_id)
    return ProjectCostResponse(**costs)


@router.get(
    "/{project_id}/profitability",
    response_model=ProjectProfitabilityResponse,
    operation_id="projects_profitability",
    summary="Get project profitability",
    description="Returns profitability analysis comparing contract/budget vs actual ticket costs.",
    responses={
        200: {"description": "Project profitability returned successfully."},
        404: {"description": "Project not found in caller scope."},
    },
)
def get_project_profitability(
    project_id: str,
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    # Verify project exists and is accessible
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_project_access(item, context)

    try:
        profitability = ProjectCostAggregation.get_project_profitability(db, project_id)
        return ProjectProfitabilityResponse(**profitability)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{project_id}/tickets",
    response_model=list[TicketResponse],
    operation_id="projects_tickets",
    summary="List project tickets",
    description="Returns all tickets linked to a project.",
    responses={
        200: {"description": "Project tickets returned successfully."},
        404: {"description": "Project not found in caller scope."},
    },
)
def get_project_tickets(
    project_id: str,
    status_filter: str | None = None,
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    # Verify project exists and is accessible
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_project_access(item, context)

    query = select(Ticket).where(Ticket.project_id == project_id)

    if status_filter:
        query = query.where(Ticket.status == status_filter)

    tickets = db.scalars(query).all()
    return tickets
