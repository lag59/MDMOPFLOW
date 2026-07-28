from __future__ import annotations

import re
from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Customer, DailyFieldReport, Material, Project
from app.schemas import AIWorkflowRouteRequest, AIWorkflowRouteResponse


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z]+", " ", value.lower()).strip()


def _extract_fields(note: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in (note or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^([A-Za-z\s]+)[:\-]\s*(.+)$", line)
        if not match:
            continue
        key = _normalize_key(match.group(1))
        value = match.group(2).strip()
        if not value:
            continue
        if key in {"company", "customer", "client"}:
            parsed["company_name"] = value
        elif key in {"supervisor", "foreman", "superintendent"}:
            parsed["reporting_supervisor"] = value
        elif key in {"work", "work performed"}:
            parsed["work_performed"] = value
        elif key in {"plan", "planned", "work planned"}:
            parsed["work_planned_for_tomorrow"] = value
        elif key in {"material", "product"}:
            parsed["material_name"] = value
    return parsed


def _resolve_report_date(value: datetime | date | None) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.utcnow()


def _resolve_project_id(db: Session, tenant_id: str, project_id: str | None) -> str | None:
    if project_id:
        return project_id
    project = db.scalar(select(Project).where(Project.tenant_id == tenant_id).order_by(Project.created_at.asc()))
    return project.id if project else None


def route_input_to_workflows(
    db: Session,
    *,
    tenant_id: str,
    actor_user_id: str,
    payload: AIWorkflowRouteRequest,
) -> AIWorkflowRouteResponse:
    parsed = _extract_fields(payload.note)
    company_name = payload.company_name or parsed.get("company_name", "")
    reporting_supervisor = payload.reporting_supervisor or parsed.get("reporting_supervisor", "")
    work_performed = payload.work_performed or parsed.get("work_performed", "")
    work_planned = payload.work_planned_for_tomorrow or parsed.get("work_planned_for_tomorrow", "")
    material_name = payload.material_name or parsed.get("material_name", "")

    customer_created = False
    if company_name.strip():
        normalized_name = company_name.strip()
        existing_customer = db.scalar(
            select(Customer).where(Customer.tenant_id == tenant_id, Customer.name.ilike(normalized_name))
        )
        if not existing_customer:
            customer = Customer(
                tenant_id=tenant_id,
                name=normalized_name,
                created_by=actor_user_id,
            )
            db.add(customer)
            db.flush()
            db.add(
                AuditLog(
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    action="ai_route_create_customer",
                    resource_type="customer",
                    resource_id=customer.id,
                    details=customer.name,
                    created_by=actor_user_id,
                )
            )
            customer_created = True

    material_created = False
    if material_name.strip():
        normalized_material = material_name.strip()
        existing_material = db.scalar(
            select(Material).where(Material.tenant_id == tenant_id, Material.name.ilike(normalized_material))
        )
        if not existing_material:
            material = Material(
                tenant_id=tenant_id,
                name=normalized_material,
                created_by=actor_user_id,
            )
            db.add(material)
            db.flush()
            db.add(
                AuditLog(
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    action="ai_route_create_material",
                    resource_type="material",
                    resource_id=material.id,
                    details=material.name,
                    created_by=actor_user_id,
                )
            )
            material_created = True

    report_created = False
    report_number = None
    project_id = _resolve_project_id(db, tenant_id, payload.project_id)
    if project_id and (company_name.strip() or reporting_supervisor.strip() or work_performed.strip() or work_planned.strip()):
        project = db.get(Project, project_id)
        if project is not None:
            report_date = _resolve_report_date(payload.report_date)
            report_number = f"DR-{project.project_number}-{report_date.strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"
            report = DailyFieldReport(
                tenant_id=tenant_id,
                project_id=project.id,
                report_number=report_number,
                report_date=report_date,
                company_name=company_name.strip(),
                reporting_supervisor=reporting_supervisor.strip(),
                work_performed=work_performed.strip(),
                work_planned_for_tomorrow=work_planned.strip(),
                status="draft",
                created_by=actor_user_id,
            )
            db.add(report)
            db.flush()
            db.add(
                AuditLog(
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    action="ai_route_create_daily_field_report",
                    resource_type="daily_field_report",
                    resource_id=report.id,
                    details=report.report_number,
                    created_by=actor_user_id,
                )
            )
            report_created = True

    db.commit()
    return AIWorkflowRouteResponse(
        routed=customer_created or material_created or report_created,
        customer_created=customer_created,
        material_created=material_created,
        report_created=report_created,
        customer_name=company_name.strip() or None,
        material_name=material_name.strip() or None,
        report_number=report_number,
        message="Captured once and routed to the right places." if (customer_created or material_created or report_created) else "No usable details were found in that note.",
    )
