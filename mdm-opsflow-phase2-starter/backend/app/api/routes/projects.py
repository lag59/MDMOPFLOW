from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, get_request_context, require_permissions
from app.models import AuditLog, Project
from app.schemas import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    tenant_id: str | None = None,
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    if "*" in context.permissions:
        if tenant_id:
            return db.scalars(select(Project).where(Project.tenant_id == tenant_id)).all()
        return db.scalars(select(Project)).all()

    assert context.membership is not None
    return db.scalars(select(Project).where(Project.tenant_id == context.membership.tenant_id)).all()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    if not context.membership and "*" not in context.permissions:
        raise HTTPException(status_code=403, detail="Tenant membership required")

    tenant_id = context.membership.tenant_id if context.membership else None
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required for platform admins")

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
    db.add(
        AuditLog(
            tenant_id=item.tenant_id,
            actor_user_id=context.user.id,
            action="create_project",
            resource_type="project",
            resource_id=item.id,
            details=item.project_name,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    if "*" not in context.permissions and (not context.membership or item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return item


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    if "*" not in context.permissions and (not context.membership or item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    db.add(
        AuditLog(
            tenant_id=item.tenant_id,
            actor_user_id=context.user.id,
            action="update_project",
            resource_type="project",
            resource_id=item.id,
            details="Updated project",
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    if "*" not in context.permissions and (not context.membership or item.tenant_id != context.membership.tenant_id):
        raise HTTPException(status_code=404, detail="Project not found")

    db.add(
        AuditLog(
            tenant_id=item.tenant_id,
            actor_user_id=context.user.id,
            action="delete_project",
            resource_type="project",
            resource_id=item.id,
            details=item.project_name,
            created_by=context.user.id,
        )
    )
    db.delete(item)
    db.commit()
    return None
