from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import quote_plus
from urllib.request import urlopen
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions, resolve_tenant_scope
from app.models import AuditLog, DailyFieldReport, Project, Ticket
from app.schemas import (
    DailyFieldReportAssistRequest,
    DailyFieldReportAssistResponse,
    DailyFieldReportCreate,
    DailyFieldReportResponse,
    DailyFieldReportUpdate,
)

router = APIRouter(prefix="/api/daily-field-reports", tags=["Daily Field Reports"])


def _tenant_id_from_context(context: RequestContext) -> str:
    return resolve_tenant_scope(context)


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


def _as_float(value: object) -> float:
    try:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return 0.0
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def _compute_rollups(item: DailyFieldReport) -> tuple[float, float, float, float]:
    crew_members = _deserialize_json_list(item.crew_members)
    equipment_used = _deserialize_json_list(item.equipment_used)
    deliveries = _deserialize_json_list(item.deliveries)

    labor_hours = 0.0
    for row in crew_members:
        count = _as_float(row.get("count", row.get("headcount", 0)))
        hours = _as_float(row.get("hours", row.get("regular_hours", 0)))
        labor_hours += count * hours

    machine_hours = 0.0
    fuel_gallons = 0.0
    for row in equipment_used:
        machine_hours += _as_float(row.get("hours", row.get("operating_hours", 0)))
        fuel_gallons += _as_float(row.get("fuel_gallons", 0))

    material_used = 0.0
    for row in deliveries:
        material_used += _as_float(row.get("used_qty", row.get("quantity", 0)))

    return labor_hours, machine_hours, material_used, fuel_gallons


def _fetch_weather_context(location: str, report_date: datetime) -> dict[str, object]:
    location_text = (location or "").strip()
    if not location_text:
        return {"source": "none", "available": False, "reason": "missing_project_address"}

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote_plus(location_text)}&count=1"
        with urlopen(geo_url, timeout=4) as response:
            geo_payload = json.loads(response.read().decode("utf-8"))
        results = geo_payload.get("results") or []
        if not results:
            return {"source": "open-meteo", "available": False, "reason": "location_not_found", "query": location_text}

        first = results[0]
        latitude = first.get("latitude")
        longitude = first.get("longitude")
        if latitude is None or longitude is None:
            return {"source": "open-meteo", "available": False, "reason": "missing_coordinates", "query": location_text}

        date_value = report_date.strftime("%Y-%m-%d")
        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}&longitude={longitude}&start_date={date_value}&end_date={date_value}"
            "&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
            "&timezone=auto"
        )
        with urlopen(weather_url, timeout=4) as response:
            weather_payload = json.loads(response.read().decode("utf-8"))

        daily = weather_payload.get("daily") or {}
        weathercode_values = daily.get("weathercode") or []
        condition = "Unknown"
        if weathercode_values:
            code = int(weathercode_values[0])
            weather_code_map = {
                0: "Clear",
                1: "Mostly clear",
                2: "Partly cloudy",
                3: "Overcast",
                45: "Fog",
                48: "Fog",
                51: "Light drizzle",
                53: "Drizzle",
                55: "Heavy drizzle",
                61: "Light rain",
                63: "Rain",
                65: "Heavy rain",
                71: "Light snow",
                73: "Snow",
                75: "Heavy snow",
                95: "Thunderstorm",
            }
            condition = weather_code_map.get(code, f"Weather code {code}")

        return {
            "source": "open-meteo",
            "available": True,
            "query": location_text,
            "resolved_location": first.get("name") or location_text,
            "latitude": latitude,
            "longitude": longitude,
            "date": date_value,
            "condition": condition,
            "temperature_max_c": (daily.get("temperature_2m_max") or [None])[0],
            "temperature_min_c": (daily.get("temperature_2m_min") or [None])[0],
            "precipitation_mm": (daily.get("precipitation_sum") or [None])[0],
            "wind_kph": (daily.get("windspeed_10m_max") or [None])[0],
        }
    except Exception:
        return {"source": "open-meteo", "available": False, "reason": "weather_service_unavailable", "query": location_text}


def _build_productivity_assist(
    *,
    payload: DailyFieldReportAssistRequest,
    project: Project,
    project_tickets: list[dict[str, Any]],
    weather_context: dict[str, object],
) -> DailyFieldReportAssistResponse:
    open_tickets = [ticket for ticket in project_tickets if str(ticket.get("status") or "").lower() not in {"closed", "resolved", "complete"}]
    assigned_dispatch = [ticket for ticket in open_tickets if str(ticket.get("truck") or "").strip() and str(ticket.get("driver") or "").strip()]
    workers = payload.total_workers or 0
    equipment_count = len(payload.equipment_used)
    precip = float(weather_context.get("precipitation_mm") or 0)
    wind = float(weather_context.get("wind_kph") or 0)

    score = 78
    score += min(8, workers)
    score += min(6, equipment_count * 2)
    score -= min(20, len(open_tickets) * 2)
    if precip >= 8:
        score -= 10
    elif precip > 0:
        score -= 4
    if wind >= 35:
        score -= 6
    score = max(25, min(99, score))

    delays: list[str] = []
    if len(open_tickets) >= 4:
        delays.append("High number of open dispatch tickets may reduce production flow.")
    if precip >= 8:
        delays.append("Heavy precipitation may slow earthwork and hauling output.")
    if wind >= 35:
        delays.append("High wind conditions may impact equipment and staging safety.")

    safety_observations: list[str] = [
        "Verify spotter coverage for backing and loading zones.",
        "Re-check traffic control at haul routes and entry points.",
    ]
    if precip > 0:
        safety_observations.append("Inspect slip hazards and muddy access routes due to precipitation.")

    dispatch_coverage = f"{len(assigned_dispatch)}/{max(1, len(open_tickets))}" if open_tickets else "0/0"
    suggested_work_performed = payload.work_performed.strip() if payload.work_performed.strip() else (
        f"Executed daily production scope for {project.project_name} with {workers or 'crew'} workers and "
        f"{equipment_count} equipment entries. Managed {len(open_tickets)} open dispatch tickets "
        f"(assigned coverage {dispatch_coverage}) while maintaining schedule and safety controls."
    )

    summary = (
        f"Productivity score {score}/100 based on crew size ({workers}), equipment entries ({equipment_count}), "
        f"open tickets ({len(open_tickets)}), and weather conditions ({weather_context.get('condition') or 'unknown'})."
    )

    return DailyFieldReportAssistResponse(
        project_id=payload.project_id,
        report_date=payload.report_date,
        ai_generated=True,
        productivity_score=score,
        productivity_summary=summary,
        suggested_work_performed=suggested_work_performed,
        suggested_delay_notes=delays,
        suggested_safety_observations=safety_observations,
        ticket_context={
            "total_project_tickets": len(project_tickets),
            "open_tickets": len(open_tickets),
            "assigned_dispatch": len(assigned_dispatch),
            "unassigned_dispatch": max(0, len(open_tickets) - len(assigned_dispatch)),
        },
        weather_context=weather_context,
    )


SECTION_FIELDS = ("crew_members", "equipment_used", "deliveries", "visitors", "delays", "photos", "production_quantities", "safety_observations")


def _prepare_report_for_response(item: DailyFieldReport) -> DailyFieldReport:
    item.weather = _deserialize_weather_value(item.weather)
    for field_name in SECTION_FIELDS:
        setattr(item, field_name, _deserialize_json_list(getattr(item, field_name)))
    return item


def _build_pdf_bytes(item: DailyFieldReport) -> bytes:
    labor_hours, machine_hours, material_used, fuel_gallons = _compute_rollups(item)
    text = "\n".join(
        [
            f"Daily Field Report: {item.report_number}",
            f"Project: {item.project_id}",
            f"Date: {item.report_date.strftime('%Y-%m-%d')}",
            f"Supervisor: {item.reporting_supervisor}",
            f"Status: {item.status}",
            f"Labor Hours Total: {labor_hours:.2f}",
            f"Machine Hours Total: {machine_hours:.2f}",
            f"Material Used Total: {material_used:.2f}",
            f"Fuel Gallons Total: {fuel_gallons:.2f}",
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


def _ensure_daily_field_reports_table(db: Session) -> None:
    # Production environments can occasionally lag migrations; this protects read/write flows.
    DailyFieldReport.__table__.create(bind=db.get_bind(), checkfirst=True)


def _find_duplicate_report(
    db: Session,
    tenant_id: str,
    project_id: str,
    report_date: datetime,
    supervisor: str,
    shift_start_time: str,
    shift_end_time: str,
) -> DailyFieldReport | None:
    _ensure_daily_field_reports_table(db)
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
    _ensure_daily_field_reports_table(db)
    query = select(DailyFieldReport).where(DailyFieldReport.tenant_id == tenant_id)
    if project_id:
        query = query.where(DailyFieldReport.project_id == project_id)
    items = db.scalars(query.order_by(DailyFieldReport.report_date.desc())).all()
    return [_prepare_report_for_response(item) for item in items]


@router.post("/assist", response_model=DailyFieldReportAssistResponse, operation_id="daily_field_reports_assist", summary="Generate AI and weather assist for a daily field report")
def assist_daily_field_report(
    payload: DailyFieldReportAssistRequest,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    project = _ensure_project_access(db, tenant_id, payload.project_id)

    def _load_ticket_context_rows() -> list[dict[str, Any]]:
        rows = db.execute(
            select(Ticket.status, Ticket.truck, Ticket.driver).where(
                Ticket.tenant_id == tenant_id,
                Ticket.project_id == payload.project_id,
            )
        ).all()
        return [{"status": row[0], "truck": row[1], "driver": row[2]} for row in rows]

    try:
        project_tickets = _load_ticket_context_rows()
    except ProgrammingError:
        # Older schemas may miss optional ticket columns referenced by ORM mappings.
        db.rollback()
        project_tickets = []

    weather_context = payload.weather.copy() if isinstance(payload.weather, dict) else {}
    if not weather_context:
        weather_context = _fetch_weather_context(project.address, payload.report_date)
    else:
        weather_context.setdefault("source", "user_input")
        weather_context.setdefault("available", True)

    return _build_productivity_assist(
        payload=payload,
        project=project,
        project_tickets=project_tickets,
        weather_context=weather_context,
    )


@router.post("", response_model=DailyFieldReportResponse, status_code=status.HTTP_201_CREATED, operation_id="daily_field_reports_create", summary="Create daily field report")
def create_daily_field_report(
    payload: DailyFieldReportCreate,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    _ensure_daily_field_reports_table(db)
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
    _ensure_daily_field_reports_table(db)
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
    _ensure_daily_field_reports_table(db)
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
    _ensure_daily_field_reports_table(db)
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
    _ensure_daily_field_reports_table(db)
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
    _ensure_daily_field_reports_table(db)
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
    _ensure_daily_field_reports_table(db)
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
    _ensure_daily_field_reports_table(db)
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
