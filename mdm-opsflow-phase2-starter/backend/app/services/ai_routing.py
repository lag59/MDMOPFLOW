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


COMPANY_KEYS = {
    "company",
    "company hauling for",
    "contractor",
    "customer",
    "client",
    "general contractor",
    "hauler",
    "owner",
    "subcontractor",
    "vendor",
}
MATERIAL_KEYS = {"aggregate", "item", "material", "material type", "product", "stone", "supply"}
SUPERVISOR_KEYS = {"foreman", "reporting supervisor", "superintendent", "supervisor"}
WORK_KEYS = {"activity", "description", "scope", "scope of work", "work", "work completed", "work performed"}
PLAN_KEYS = {"next steps", "plan", "planned", "tomorrow", "work planned", "work planned for tomorrow"}

COMMON_MATERIAL_PATTERNS = (
    r"\b(?:#\s*)?57\s+stone\b",
    r"\b(?:#\s*)?67\s+stone\b",
    r"\b(?:#\s*)?78\s+stone\b",
    r"\b(?:#\s*)?4\s+stone\b",
    r"\bcrushed\s+stone\b",
    r"\bbase\s+rock\b",
    r"\brip\s*rap\b",
    r"\baggregate\b",
    r"\bgravel\b",
    r"\bsand\b",
    r"\btopsoil\b",
    r"\bfill\s+dirt\b",
    r"\bborrow\s+fill\b",
    r"\bconcrete\b",
    r"\basphalt\b",
)


def _clean_value(value: str) -> str:
    return (value or "").strip().strip(" .;,|")


def _set_if_missing(parsed: dict[str, str], key: str, value: str | None) -> None:
    cleaned = _clean_value(value or "")
    if cleaned and not parsed.get(key):
        parsed[key] = cleaned


def _extract_labeled_value(label_pattern: str, note: str) -> str:
    match = re.search(
        rf"(?im)^\s*(?:{label_pattern})\s*(?::|#|-)?\s+(.+?)\s*$",
        note,
    )
    return _clean_value(match.group(1)) if match else ""


def _extract_common_material(note: str) -> str:
    for pattern in COMMON_MATERIAL_PATTERNS:
        match = re.search(pattern, note, flags=re.IGNORECASE)
        if match:
            return _clean_value(match.group(0))
    return ""


def _extract_work_sentence(note: str) -> str:
    normalized = re.sub(r"\s+", " ", note).strip()
    if not normalized:
        return ""
    match = re.search(
        r"\b(completed|placed|installed|imported|exported|excavated|hauled|graded|poured|backfilled)\b(.{0,180})",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        return _clean_value(match.group(0))
    return ""


def _extract_probable_company(note: str) -> str:
    labeled = _extract_labeled_value(
        r"(?:company|company\s+hauling\s+for|contractor|customer|client|general\s+contractor|hauler|owner|subcontractor|vendor)",
        note,
    )
    if labeled:
        return labeled

    match = re.search(
        r"\b([A-Z][A-Za-z0-9&.,' -]{2,80}\b(?:Builders|Construction|Contracting|Contractors|Civil|Hauling|Services|Supply|Materials|Excavating|Paving|LLC|Inc\.?|Corp\.?))\b",
        note,
    )
    return _clean_value(match.group(1)) if match else ""


def _extract_fields(note: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in (note or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^([A-Za-z\s/]+?)\s*(?::|#|-)\s*(.+)$", line)
        if not match:
            continue
        key = _normalize_key(match.group(1))
        value = _clean_value(match.group(2))
        if not value:
            continue
        if key in COMPANY_KEYS:
            _set_if_missing(parsed, "company_name", value)
        elif key in SUPERVISOR_KEYS:
            _set_if_missing(parsed, "reporting_supervisor", value)
        elif key in WORK_KEYS:
            _set_if_missing(parsed, "work_performed", value)
        elif key in PLAN_KEYS:
            _set_if_missing(parsed, "work_planned_for_tomorrow", value)
        elif key in MATERIAL_KEYS:
            _set_if_missing(parsed, "material_name", value)

    _set_if_missing(parsed, "company_name", _extract_probable_company(note))
    _set_if_missing(parsed, "material_name", _extract_common_material(note))
    _set_if_missing(parsed, "work_performed", _extract_labeled_value(r"scope\s+of\s+work|work\s+performed|work\s+completed", note))
    _set_if_missing(parsed, "work_performed", _extract_work_sentence(note))
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
    recognized_details = any(
        value.strip()
        for value in (company_name, reporting_supervisor, work_performed, work_planned, material_name)
    )

    customer_created = False
    customer_recognized_existing = False
    if company_name.strip():
        normalized_name = company_name.strip()
        existing_customer = db.scalar(
            select(Customer).where(Customer.tenant_id == tenant_id, Customer.name.ilike(normalized_name))
        )
        if existing_customer:
            customer_recognized_existing = True
        else:
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
    material_recognized_existing = False
    if material_name.strip():
        normalized_material = material_name.strip()
        existing_material = db.scalar(
            select(Material).where(Material.tenant_id == tenant_id, Material.name.ilike(normalized_material))
        )
        if existing_material:
            material_recognized_existing = True
        else:
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
    created_count = sum(1 for value in (customer_created, material_created, report_created) if value)
    recognized_existing_count = sum(1 for value in (customer_recognized_existing, material_recognized_existing) if value)
    useful_details_count = sum(
        1
        for value in (company_name, reporting_supervisor, work_performed, work_planned, material_name)
        if value.strip()
    )
    if created_count > 0:
        processing_outcome = "created"
        message = f"Created {created_count} new record{'' if created_count == 1 else 's'}."
    elif recognized_existing_count > 0:
        processing_outcome = "recognized_existing"
        message = f"Recognized {recognized_existing_count} existing record{'' if recognized_existing_count == 1 else 's'}; no duplicate rows were created."
    elif useful_details_count > 0:
        processing_outcome = "needs_review"
        message = "Document was recognized and useful details were extracted, but no new database rows were required."
    else:
        processing_outcome = "no_useful_data"
        message = "Document was processed, but no actionable data was identified."

    return AIWorkflowRouteResponse(
        routed=processing_outcome != "no_useful_data",
        processing_outcome=processing_outcome,
        created_count=created_count,
        recognized_existing_count=recognized_existing_count,
        useful_details_count=useful_details_count,
        customer_created=customer_created,
        material_created=material_created,
        report_created=report_created,
        customer_name=company_name.strip() or None,
        material_name=material_name.strip() or None,
        report_number=report_number,
        message=message,
    )
