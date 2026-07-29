from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import AuditLog, PayrollRun, PayrollTimecard
from app.schemas import (
    PayrollRunCreate,
    PayrollRunResponse,
    PayrollSummaryByProjectResponse,
    PayrollSummaryResponse,
    PayrollTimecardCreate,
    PayrollTimecardResponse,
    PayrollTimecardUpdate,
)

router = APIRouter(prefix="/api/payroll", tags=["Payroll"])


def _require_tenant(context: RequestContext) -> str:
    tenant_id = context.membership.tenant_id if context.membership else context.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")
    return tenant_id


@router.get(
    "/timecards",
    response_model=list[PayrollTimecardResponse],
    operation_id="payroll_timecards_list",
    summary="List payroll timecards",
)
def list_timecards(
    context: RequestContext = Depends(require_permissions("payroll_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(PayrollTimecard)
        .where(PayrollTimecard.tenant_id == tenant_id)
        .order_by(PayrollTimecard.work_date.desc(), PayrollTimecard.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/timecards",
    response_model=PayrollTimecardResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="payroll_timecards_create",
    summary="Create payroll timecard",
)
def create_timecard(
    payload: PayrollTimecardCreate,
    context: RequestContext = Depends(require_permissions("payroll_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = PayrollTimecard(
        tenant_id=tenant_id,
        employee_id=payload.employee_id,
        project_id=payload.project_id,
        work_date=payload.work_date,
        regular_hours=payload.regular_hours,
        overtime_hours=payload.overtime_hours,
        double_time_hours=payload.double_time_hours,
        cost_code=payload.cost_code,
        work_description=payload.work_description,
        status=payload.status,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_payroll_timecard",
            resource_type="payroll_timecard",
            resource_id=item.id,
            details=item.work_description or item.employee_id,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch(
    "/timecards/{timecard_id}",
    response_model=PayrollTimecardResponse,
    operation_id="payroll_timecards_update",
    summary="Update payroll timecard",
)
def update_timecard(
    timecard_id: str,
    payload: PayrollTimecardUpdate,
    context: RequestContext = Depends(require_permissions("payroll_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = db.get(PayrollTimecard, timecard_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Payroll timecard not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/runs",
    response_model=list[PayrollRunResponse],
    operation_id="payroll_runs_list",
    summary="List payroll runs",
)
def list_runs(
    context: RequestContext = Depends(require_permissions("payroll_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(PayrollRun)
        .where(PayrollRun.tenant_id == tenant_id)
        .order_by(PayrollRun.period_end.desc(), PayrollRun.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/runs",
    response_model=PayrollRunResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="payroll_runs_create",
    summary="Create payroll run",
)
def create_run(
    payload: PayrollRunCreate,
    context: RequestContext = Depends(require_permissions("payroll_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    timecards = db.scalars(
        select(PayrollTimecard).where(
            PayrollTimecard.tenant_id == tenant_id,
            PayrollTimecard.work_date >= payload.period_start,
            PayrollTimecard.work_date <= payload.period_end,
        )
    ).all()

    employee_ids = {item.employee_id for item in timecards}
    total_regular_hours = sum(float(item.regular_hours or 0) for item in timecards)
    total_overtime_hours = sum(float(item.overtime_hours or 0) for item in timecards)
    total_double_time_hours = sum(float(item.double_time_hours or 0) for item in timecards)

    item = PayrollRun(
        id=str(uuid4()),
        tenant_id=tenant_id,
        run_number=payload.run_number,
        period_start=payload.period_start,
        period_end=payload.period_end,
        status=payload.status,
        employee_count=len(employee_ids),
        total_regular_hours=total_regular_hours,
        total_overtime_hours=total_overtime_hours,
        total_double_time_hours=total_double_time_hours,
        notes=payload.notes,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_payroll_run",
            resource_type="payroll_run",
            resource_id=item.id,
            details=item.run_number,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/summary",
    response_model=PayrollSummaryResponse,
    operation_id="payroll_summary_get",
    summary="Get payroll summary",
)
def get_summary(
    context: RequestContext = Depends(require_permissions("payroll_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    timecards = db.scalars(select(PayrollTimecard).where(PayrollTimecard.tenant_id == tenant_id)).all()
    runs = db.scalars(select(PayrollRun).where(PayrollRun.tenant_id == tenant_id)).all()

    employee_ids = {item.employee_id for item in timecards}
    by_project: dict[str, PayrollSummaryByProjectResponse] = {}
    grouped_hours = defaultdict(
        lambda: {"regular": Decimal("0.00"), "overtime": Decimal("0.00"), "double": Decimal("0.00"), "timecards": 0}
    )
    for item in timecards:
        project_key = item.project_id or "unassigned"
        grouped_hours[project_key]["regular"] += Decimal(str(item.regular_hours or 0))
        grouped_hours[project_key]["overtime"] += Decimal(str(item.overtime_hours or 0))
        grouped_hours[project_key]["double"] += Decimal(str(item.double_time_hours or 0))
        grouped_hours[project_key]["timecards"] += 1

    project_summaries = [
        PayrollSummaryByProjectResponse(
            project_id=None if key == "unassigned" else key,
            timecard_count=value["timecards"],
            regular_hours=value["regular"],
            overtime_hours=value["overtime"],
            double_time_hours=value["double"],
        )
        for key, value in grouped_hours.items()
    ]

    return PayrollSummaryResponse(
        employee_count=len(employee_ids),
        timecard_count=len(timecards),
        payroll_run_count=len(runs),
        total_regular_hours=sum((Decimal(str(item.regular_hours or 0)) for item in timecards), Decimal("0.00")),
        total_overtime_hours=sum((Decimal(str(item.overtime_hours or 0)) for item in timecards), Decimal("0.00")),
        total_double_time_hours=sum((Decimal(str(item.double_time_hours or 0)) for item in timecards), Decimal("0.00")),
        by_project=project_summaries,
    )
