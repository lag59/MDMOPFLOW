from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import AuditLog, DailyFieldReport, Project
from app.schemas import (
    DailyFieldReportCreate,
    DailyFieldReportResponse,
    DailyFieldReportUpdate,
)

router = APIRouter(prefix="/api/daily-field-reports", tags=["Daily Field Reports"])


def _tenant_id_from_context(context: RequestContext) -> str:
    if context.tenant_id:
        return context.tenant_id
    if context.membership:
        return context.membership.tenant_id
    raise HTTPException(status_code=400, detail="X-Tenant-ID is required for platform admins")


def _ensure_project_access(db: Session, tenant_id: str, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project or project.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _build_report_number(project: Project, report_date: datetime) -> str:
    date_stamp = report_date.strftime("%Y%m%d")
    return f"DR-{project.project_number}-{date_stamp}-{uuid4().hex[:4].upper()}"


def _serialize_weather_value(value: object) -> str:
    if value is None:
        return "{}"
    if isinstance(value, str):
        return value.strip() or "{}"
    return json.dumps(value)


def _deserialize_weather_value(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"value": text}
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    return {"value": value}


def _serialize_json_field(value: object) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        return value.strip() or "[]"
    return json.dumps(value)


def _deserialize_json_list(value: object) -> list[dict[str, object]]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return [{"value": text}]
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    return [{"value": value}]


SECTION_FIELDS = ("crew_members", "equipment_used", "deliveries", "visitors", "delays", "photos", "production_quantities", "safety_observations")


def _prepare_report_for_response(item: DailyFieldReport) -> DailyFieldReport:
    item.weather = _deserialize_weather_value(item.weather)
    for field_name in SECTION_FIELDS:
        setattr(item, field_name, _deserialize_json_list(getattr(item, field_name)))
    return item


def _build_pdf_bytes(item: DailyFieldReport) -> bytes:
    text = "\n".join(
        [
            f"Daily Field Report: {item.report_number}",
            f"Project: {item.project_id}",
            f"Date: {item.report_date.strftime('%Y-%m-%d')}",
            f"Supervisor: {item.reporting_supervisor}",
            f"Status: {item.status}",
        ]
    )
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj")
    objects.append(b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj")
    stream_text = f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET"
    stream_bytes = stream_text.encode("latin-1", "ignore")
    objects.append(f"4 0 obj<< /Length {len(stream_bytes)} >>stream\n{stream_text}\nendstream\nendobj".encode("latin-1", "ignore"))
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj")

    pdf_bytes = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf_bytes))
        pdf_bytes.extend(obj)
        pdf_bytes.extend(b"\n")

    xref_offset = len(pdf_bytes)
    pdf_bytes.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf_bytes.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf_bytes.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf_bytes.extend(f"trailer<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(pdf_bytes)


def _find_duplicate_report(
    db: Session,
    tenant_id: str,
    project_id: str,
    report_date: datetime,
    supervisor: str,
    shift_start_time: str,
    shift_end_time: str,
) -> DailyFieldReport | None:
    normalized_supervisor = (supervisor or "").strip().lower()
    if not normalized_supervisor:
        return None
    return db.scalars(
        select(DailyFieldReport).where(
            DailyFieldReport.tenant_id == tenant_id,
            DailyFieldReport.project_id == project_id,
            DailyFieldReport.report_date == report_date,
            DailyFieldReport.reporting_supervisor.ilike(supervisor),
            DailyFieldReport.shift_start_time == shift_start_time,
            DailyFieldReport.shift_end_time == shift_end_time,
            DailyFieldReport.status != "approved",
        )
    ).first()


@router.get("", response_model=list[DailyFieldReportResponse], operation_id="daily_field_reports_list", summary="List daily field reports")
def list_daily_field_reports(
    project_id: str | None = Query(default=None),
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    query = select(DailyFieldReport).where(DailyFieldReport.tenant_id == tenant_id)
    if project_id:
        query = query.where(DailyFieldReport.project_id == project_id)
    items = db.scalars(query.order_by(DailyFieldReport.report_date.desc())).all()
    return [_prepare_report_for_response(item) for item in items]


@router.post("", response_model=DailyFieldReportResponse, status_code=status.HTTP_201_CREATED, operation_id="daily_field_reports_create", summary="Create daily field report")
def create_daily_field_report(
    payload: DailyFieldReportCreate,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    _ensure_project_access(db, tenant_id, payload.project_id)

    report_date = payload.report_date
    duplicate = _find_duplicate_report(
        db,
        tenant_id=tenant_id,
        project_id=payload.project_id,
        report_date=report_date,
        supervisor=payload.reporting_supervisor,
        shift_start_time=payload.shift_start_time,
        shift_end_time=payload.shift_end_time,
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Duplicate daily report already exists for this project, date, and supervisor")

    project = db.get(Project, payload.project_id)
    weather_payload = payload.weather
    if weather_payload is None:
        weather_value = "{}"
    elif isinstance(weather_payload, str):
        weather_value = weather_payload
    else:
        weather_value = json.dumps(weather_payload)

    item = DailyFieldReport(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        report_number=_build_report_number(project, report_date),
        report_date=report_date,
        company_name=payload.company_name,
        reporting_supervisor=payload.reporting_supervisor,
        shift_start_time=payload.shift_start_time,
        shift_end_time=payload.shift_end_time,
        weather=weather_value,
        crew_members=_serialize_json_field(payload.crew_members),
        equipment_used=_serialize_json_field(payload.equipment_used),
        deliveries=_serialize_json_field(payload.deliveries),
        visitors=_serialize_json_field(payload.visitors),
        delays=_serialize_json_field(payload.delays),
        photos=_serialize_json_field(payload.photos),
        production_quantities=_serialize_json_field(payload.production_quantities),
        safety_observations=_serialize_json_field(payload.safety_observations),
        work_performed=payload.work_performed,
        work_planned_for_tomorrow=payload.work_planned_for_tomorrow,
        prepared_by=payload.prepared_by,
        electronic_signature=payload.electronic_signature,
        status=payload.status,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_daily_field_report",
            resource_type="daily_field_report",
            resource_id=item.id,
            details=item.report_number,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return _prepare_report_for_response(item)


@router.get("/{report_id}", response_model=DailyFieldReportResponse, operation_id="daily_field_reports_get", summary="Get daily field report")
def get_daily_field_report(
    report_id: str,
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    item = db.get(DailyFieldReport, report_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Daily field report not found")
    return _prepare_report_for_response(item)


@router.patch("/{report_id}", response_model=DailyFieldReportResponse, operation_id="daily_field_reports_update", summary="Update daily field report")
def update_daily_field_report(
    report_id: str,
    payload: DailyFieldReportUpdate,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    item = db.get(DailyFieldReport, report_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Daily field report not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "weather":
            value = _serialize_weather_value(value)
        elif key in SECTION_FIELDS:
            value = _serialize_json_field(value)
        setattr(item, key, value)

    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="update_daily_field_report",
            resource_type="daily_field_report",
            resource_id=item.id,
            details="Updated daily field report",
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return _prepare_report_for_response(item)


@router.post("/{report_id}/submit", response_model=DailyFieldReportResponse, operation_id="daily_field_reports_submit", summary="Submit daily field report")
def submit_daily_field_report(
    report_id: str,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    item = db.get(DailyFieldReport, report_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Daily field report not found")

    item.status = "submitted"
    item.submitted_by = context.user.id
    item.submitted_at = datetime.utcnow()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="submit_daily_field_report",
            resource_type="daily_field_report",
            resource_id=item.id,
            details="Submitted daily field report",
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return _prepare_report_for_response(item)


@router.post("/{report_id}/review", response_model=DailyFieldReportResponse, operation_id="daily_field_reports_review", summary="Review daily field report")
def review_daily_field_report(
    report_id: str,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    item = db.get(DailyFieldReport, report_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Daily field report not found")

    item.status = "reviewed"
    item.reviewed_by = context.user.id
    item.reviewed_at = datetime.utcnow()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="review_daily_field_report",
            resource_type="daily_field_report",
            resource_id=item.id,
            details="Reviewed daily field report",
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return _prepare_report_for_response(item)


@router.post("/{report_id}/return", response_model=DailyFieldReportResponse, operation_id="daily_field_reports_return", summary="Return daily field report for correction")
def return_daily_field_report(
    report_id: str,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    item = db.get(DailyFieldReport, report_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Daily field report not found")

    item.status = "returned"
    item.approved_by = None
    item.approved_at = None
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="return_daily_field_report",
            resource_type="daily_field_report",
            resource_id=item.id,
            details="Returned daily field report for correction",
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return _prepare_report_for_response(item)


@router.get("/{report_id}/pdf", response_class=Response, operation_id="daily_field_reports_pdf", summary="Export daily field report as PDF")
def export_daily_field_report_pdf(
    report_id: str,
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    item = db.get(DailyFieldReport, report_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Daily field report not found")

    pdf_bytes = _build_pdf_bytes(_prepare_report_for_response(item))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={item.report_number}.pdf"},
    )


@router.post("/{report_id}/approve", response_model=DailyFieldReportResponse, operation_id="daily_field_reports_approve", summary="Approve daily field report")
def approve_daily_field_report(
    report_id: str,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    item = db.get(DailyFieldReport, report_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Daily field report not found")

    item.status = "approved"
    item.approved_by = context.user.id
    item.approved_at = datetime.utcnow()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="approve_daily_field_report",
            resource_type="daily_field_report",
            resource_id=item.id,
            details="Approved daily field report",
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return _prepare_report_for_response(item)
