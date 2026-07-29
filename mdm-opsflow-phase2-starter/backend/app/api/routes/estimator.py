from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import (
    AuditLog,
    EstimatorBidPipelineItem,
    EstimatorTakeoff,
    EstimatorVersion,
    EstimatorWinLossRecord,
)
from app.schemas import (
    EstimatorBidPipelineItemCreate,
    EstimatorBidPipelineItemResponse,
    EstimatorSummaryResponse,
    EstimatorTakeoffCreate,
    EstimatorTakeoffResponse,
    EstimatorVersionCreate,
    EstimatorVersionResponse,
    EstimatorWinLossRecordCreate,
    EstimatorWinLossRecordResponse,
)

router = APIRouter(prefix="/api/estimator", tags=["Estimator"])


def _require_tenant(context: RequestContext) -> str:
    tenant_id = context.membership.tenant_id if context.membership else context.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")
    return tenant_id


@router.get(
    "/takeoffs",
    response_model=list[EstimatorTakeoffResponse],
    operation_id="estimator_takeoffs_list",
    summary="List estimator takeoffs",
)
def list_takeoffs(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(EstimatorTakeoff)
        .where(EstimatorTakeoff.tenant_id == tenant_id)
        .order_by(EstimatorTakeoff.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/takeoffs",
    response_model=EstimatorTakeoffResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimator_takeoffs_create",
    summary="Create estimator takeoff",
)
def create_takeoff(
    payload: EstimatorTakeoffCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = EstimatorTakeoff(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        takeoff_number=payload.takeoff_number,
        material_name=payload.material_name,
        quantity=payload.quantity,
        unit_of_measure=payload.unit_of_measure,
        estimated_cost=payload.estimated_cost,
        status=payload.status,
        notes=payload.notes,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_estimator_takeoff",
            resource_type="estimator_takeoff",
            resource_id=item.id,
            details=item.takeoff_number,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/versions",
    response_model=list[EstimatorVersionResponse],
    operation_id="estimator_versions_list",
    summary="List estimate versions",
)
def list_versions(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(EstimatorVersion)
        .where(EstimatorVersion.tenant_id == tenant_id)
        .order_by(EstimatorVersion.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/versions",
    response_model=EstimatorVersionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimator_versions_create",
    summary="Create estimate version",
)
def create_version(
    payload: EstimatorVersionCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = EstimatorVersion(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        version_name=payload.version_name,
        revision_number=payload.revision_number,
        estimated_revenue=payload.estimated_revenue,
        estimated_cost=payload.estimated_cost,
        status=payload.status,
        notes=payload.notes,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_estimator_version",
            resource_type="estimator_version",
            resource_id=item.id,
            details=f"{item.version_name} r{item.revision_number}",
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/bid-pipeline",
    response_model=list[EstimatorBidPipelineItemResponse],
    operation_id="estimator_bid_pipeline_list",
    summary="List estimator bid pipeline",
)
def list_bid_pipeline(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(EstimatorBidPipelineItem)
        .where(EstimatorBidPipelineItem.tenant_id == tenant_id)
        .order_by(EstimatorBidPipelineItem.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/bid-pipeline",
    response_model=EstimatorBidPipelineItemResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimator_bid_pipeline_create",
    summary="Create estimator bid pipeline item",
)
def create_bid_pipeline_item(
    payload: EstimatorBidPipelineItemCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = EstimatorBidPipelineItem(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        bid_number=payload.bid_number,
        customer_name=payload.customer_name,
        stage=payload.stage,
        bid_amount=payload.bid_amount,
        probability_percent=payload.probability_percent,
        due_date=payload.due_date,
        status=payload.status,
        notes=payload.notes,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_estimator_bid_pipeline_item",
            resource_type="estimator_bid_pipeline_item",
            resource_id=item.id,
            details=item.bid_number,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/win-loss",
    response_model=list[EstimatorWinLossRecordResponse],
    operation_id="estimator_win_loss_list",
    summary="List estimator win/loss records",
)
def list_win_loss_records(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(EstimatorWinLossRecord)
        .where(EstimatorWinLossRecord.tenant_id == tenant_id)
        .order_by(EstimatorWinLossRecord.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/win-loss",
    response_model=EstimatorWinLossRecordResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimator_win_loss_create",
    summary="Create estimator win/loss record",
)
def create_win_loss_record(
    payload: EstimatorWinLossRecordCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = EstimatorWinLossRecord(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        bid_pipeline_item_id=payload.bid_pipeline_item_id,
        outcome=payload.outcome,
        final_amount=payload.final_amount,
        decision_date=payload.decision_date,
        reason=payload.reason,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_estimator_win_loss_record",
            resource_type="estimator_win_loss_record",
            resource_id=item.id,
            details=item.outcome,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/summary",
    response_model=EstimatorSummaryResponse,
    operation_id="estimator_summary_get",
    summary="Get estimator workflow summary",
)
def get_summary(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    takeoffs = db.scalars(select(EstimatorTakeoff).where(EstimatorTakeoff.tenant_id == tenant_id)).all()
    versions = db.scalars(select(EstimatorVersion).where(EstimatorVersion.tenant_id == tenant_id)).all()
    bids = db.scalars(select(EstimatorBidPipelineItem).where(EstimatorBidPipelineItem.tenant_id == tenant_id)).all()
    outcomes = db.scalars(select(EstimatorWinLossRecord).where(EstimatorWinLossRecord.tenant_id == tenant_id)).all()

    wins = sum(1 for item in outcomes if item.outcome == "won")
    losses = sum(1 for item in outcomes if item.outcome == "lost")
    pending = sum(1 for item in outcomes if item.outcome not in {"won", "lost"})
    decided = wins + losses
    win_rate_percent = (Decimal(wins) / Decimal(decided) * Decimal("100.00")) if decided else Decimal("0.00")

    return EstimatorSummaryResponse(
        takeoff_count=len(takeoffs),
        version_count=len(versions),
        bid_pipeline_count=len(bids),
        wins=wins,
        losses=losses,
        pending=pending,
        win_rate_percent=win_rate_percent.quantize(Decimal("0.01")),
    )
