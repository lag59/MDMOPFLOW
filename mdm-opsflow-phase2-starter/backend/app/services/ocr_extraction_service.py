"""
OCR Extraction Service â€” bridges intake OCR results into structured DocumentExtraction records.

Flow:
  IntakeItem (extracted_text + extracted_entities populated on upload)
      â†“ trigger_extraction_for_intake()
  extract_ticket_candidates() â€” full regex field extraction
      â†“
  _map_fields_to_extraction() â€” confidence-scored mapping to DocumentExtraction
      â†“
  _generate_issues() â€” flag missing required / low-confidence fields as ExtractionIssue rows
      â†“
  DocumentExtraction (status=review_pending) + ExtractionIssue[]
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import DocumentExtraction, ExtractionCanonicalFact, ExtractionDiscrepancy, ExtractionIssue, IntakeItem
from app.services.bid_package_extraction import build_bid_package_payload
from app.services.canonical_intake import ESTIMATOR_DOCUMENT_TYPES, build_canonical_document, score_canonical_document
from app.services.ticket_extractor import extract_ticket_candidates


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Required / important field definitions
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

REQUIRED_FIELDS_BY_PROFILE: dict[str, list[tuple[str, str]]] = {
    "ticket": [
        ("ticket_number", "Ticket Number"),
        ("driver_name", "Driver Name"),
        ("material", "Material"),
    ],
    "estimator": [
        ("project_name", "Project Name"),
    ],
    "accounting": [
        ("invoice_number", "Invoice Number"),
    ],
}

IMPORTANT_FIELDS_BY_PROFILE: dict[str, list[tuple[str, str]]] = {
    "ticket": [
        ("truck_number", "Truck Number"),
        ("destination", "Destination / Dump Site"),
        ("job_location", "Job Location"),
        ("company_name", "Hauling Company"),
        ("ticket_date", "Ticket Date"),
    ],
    "estimator": [
        ("job_number", "Project Number"),
        ("company_name", "Vendor / Subcontractor"),
        ("ticket_number", "Document Reference Number"),
    ],
    "accounting": [
        ("company_name", "Vendor"),
        ("invoice_total", "Invoice Total"),
    ],
}

# Base confidence given to a regex-matched field (no character-level score available)
_REGEX_MATCH_CONFIDENCE = 0.80

# Confidence penalty applied when the overall OCR text confidence is low
_OCR_LOW_CONFIDENCE_PENALTY = 0.15


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Date/time helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_DATE_FORMATS = (
    "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y",
    "%d/%m/%Y", "%d-%m-%Y",
    "%Y-%m-%d",
)

_TIME_FORMATS = (
    "%I:%M %p", "%I:%M%p", "%I.%M %p", "%I.%M%p",
    "%H:%M", "%H.%M",
)


def _parse_date(value: str) -> Optional[datetime]:
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def _parse_time(value: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
    value = value.strip()
    ref = reference_date or datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    for fmt in _TIME_FORMATS:
        try:
            t = datetime.strptime(value, fmt)
            return ref.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        except ValueError:
            pass
    return None


def _parse_float(value: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d.]", "", value)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _parse_int(value: str) -> Optional[int]:
    cleaned = re.sub(r"[^\d]", "", value)
    try:
        return int(cleaned) if cleaned else None
    except ValueError:
        return None


def _confidence(value: str, base_confidence: float) -> float:
    """Return base_confidence if value is non-empty, else 0."""
    return base_confidence if value and value.strip() else 0.0


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Field â†’ DocumentExtraction mapping
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _map_candidates_to_extraction(
    candidates: list[dict[str, str]],
    ocr_confidence: float,
    raw_text: str,
    tenant_id: str,
    intake_item_id: str,
    user_id: str,
) -> tuple[DocumentExtraction, list[dict]]:
    """
    Map ticket_extractor candidate dicts â†’ DocumentExtraction ORM instance.
    Returns (extraction, raw_issue_dicts) where issues are created separately.
    """
    # Use first candidate as primary; merge remaining for missing fields
    merged: dict[str, str] = {}
    for candidate in reversed(candidates):
        merged.update(candidate)
    # Primary candidate wins over merged
    if candidates:
        merged.update(candidates[0])

    conf = max(0.0, min(1.0, _REGEX_MATCH_CONFIDENCE - (
        _OCR_LOW_CONFIDENCE_PENALTY if ocr_confidence < 0.6 else 0.0
    )))

    # â”€â”€ Dates â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ticket_date = _parse_date(merged.get("date", ""))
    start_time = _parse_time(merged.get("start_time", ""), ticket_date)
    finish_time = _parse_time(merged.get("finish_time", ""), ticket_date)

    total_hours: Optional[float] = None
    if start_time and finish_time and finish_time > start_time:
        delta = finish_time - start_time
        total_hours = round(delta.total_seconds() / 3600, 2)

    # â”€â”€ Weights â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    net_lbs = _parse_float(merged.get("net_weight_lbs", ""))
    tons: Optional[float] = None
    if net_lbs:
        tons = round(net_lbs / 2000.0, 3)

    # â”€â”€ Document type classification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    has_invoice = bool(merged.get("invoice_number") or merged.get("invoice_total"))
    doc_type = "invoice" if has_invoice else "ticket"
    doc_type_conf = conf if merged.get("ticket_number") or merged.get("invoice_number") else 0.4

    # â”€â”€ Truck type â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    truck_type = ""
    truck_raw = merged.get("truck", "")
    if truck_raw:
        for known in ("tandem", "tri-axle", "triaxle", "quad", "quint", "semi"):
            if known in truck_raw.lower():
                truck_type = known.capitalize()
                break

    # â”€â”€ Notes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    notes_parts = [v for k, v in merged.items() if k in ("special_comments",) and v]

    extraction = DocumentExtraction(
        id=str(uuid4()),
        tenant_id=tenant_id,
        intake_item_id=intake_item_id,
        # Classification
        document_type=doc_type,
        document_type_confidence=doc_type_conf,
        is_multi_document=len(candidates) > 1,
        document_count=max(1, len(candidates)),
        # Company
        company_name=merged.get("company_hauling_for", ""),
        company_name_confidence=_confidence(merged.get("company_hauling_for", ""), conf),
        # IDs
        ticket_number=merged.get("ticket_number", ""),
        ticket_number_confidence=_confidence(merged.get("ticket_number", ""), conf),
        invoice_number=merged.get("invoice_number", ""),
        invoice_number_confidence=_confidence(merged.get("invoice_number", ""), conf),
        job_number=merged.get("job", ""),
        job_number_confidence=_confidence(merged.get("job", ""), conf),
        # Dates
        ticket_date=ticket_date,
        ticket_date_confidence=_confidence(merged.get("date", ""), conf),
        start_time=start_time,
        start_time_confidence=_confidence(merged.get("start_time", ""), conf),
        finish_time=finish_time,
        finish_time_confidence=_confidence(merged.get("finish_time", ""), conf),
        total_hours_calculated=total_hours,
        # Customer / project
        customer_name=merged.get("contractor", ""),
        customer_name_confidence=_confidence(merged.get("contractor", ""), conf),
        project_name=merged.get("job", ""),
        project_name_confidence=_confidence(merged.get("job", ""), conf),
        job_location=merged.get("job_location", ""),
        job_location_confidence=_confidence(merged.get("job_location", ""), conf),
        # Driver
        driver_name=merged.get("driver", ""),
        driver_name_confidence=_confidence(merged.get("driver", ""), conf),
        # Truck
        truck_number=merged.get("truck", ""),
        truck_number_confidence=_confidence(merged.get("truck", ""), conf),
        truck_type=truck_type,
        truck_type_confidence=_confidence(truck_type, conf),
        # Material
        material=merged.get("material", ""),
        material_confidence=_confidence(merged.get("material", ""), conf),
        material_category=_classify_material(merged.get("material", "")),
        # Destination â€” ticket_extractor uses "job_location" for the site
        destination=merged.get("job_location", ""),
        destination_confidence=_confidence(merged.get("job_location", ""), conf),
        # Quantities
        load_count=_parse_int(merged.get("number_of_loads", "")),
        load_count_confidence=_confidence(merged.get("number_of_loads", ""), conf),
        weight_net_lbs=net_lbs,
        weight_net_lbs_confidence=_confidence(merged.get("net_weight_lbs", ""), conf),
        tons=tons,
        # Status
        status="review_pending",
        # OCR raw
        ocr_raw_text=raw_text,
        extracted_notes="; ".join(notes_parts),
        # Audit
        created_by=user_id,
    )

    # â”€â”€ Generate issue list â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    issues = _generate_issues(extraction, profile_key="ticket")

    return extraction, issues


def _map_canonical_to_extraction(
    *,
    canonical_doc,
    routing_scores,
    raw_text: str,
    tenant_id: str,
    intake_item_id: str,
    user_id: str,
) -> DocumentExtraction:
    reference_number = canonical_doc.document_reference_number
    invoice_number = reference_number if canonical_doc.document_type == "invoice" else ""
    ticket_number = reference_number if canonical_doc.document_type != "invoice" else ""
    doc_confidence = max(
        canonical_doc.confidence,
        routing_scores.estimator_document_score,
        routing_scores.accounting_document_score,
    )

    return DocumentExtraction(
        id=str(uuid4()),
        tenant_id=tenant_id,
        intake_item_id=intake_item_id,
        document_type=canonical_doc.document_type,
        document_type_confidence=doc_confidence,
        is_multi_document=False,
        document_count=1,
        company_name=canonical_doc.vendor.get("name", "") or canonical_doc.entities.get("contractor", ""),
        company_name_confidence=doc_confidence,
        ticket_number=ticket_number,
        ticket_number_confidence=doc_confidence if ticket_number else 0.0,
        invoice_number=invoice_number,
        invoice_number_confidence=doc_confidence if invoice_number else 0.0,
        job_number=canonical_doc.project.get("project_number", ""),
        job_number_confidence=doc_confidence if canonical_doc.project.get("project_number", "") else 0.0,
        customer_name=canonical_doc.entities.get("owner", "") or canonical_doc.entities.get("general_contractor", ""),
        customer_name_confidence=0.7 if (canonical_doc.entities.get("owner", "") or canonical_doc.entities.get("general_contractor", "")) else 0.0,
        project_name=canonical_doc.project.get("project_name", ""),
        project_name_confidence=doc_confidence if canonical_doc.project.get("project_name", "") else 0.0,
        job_location=canonical_doc.entities.get("location", "") or canonical_doc.entities.get("job_location", ""),
        job_location_confidence=0.75 if (canonical_doc.entities.get("location", "") or canonical_doc.entities.get("job_location", "")) else 0.0,
        driver_name=canonical_doc.entities.get("driver", ""),
        driver_name_confidence=0.8 if canonical_doc.entities.get("driver", "") else 0.0,
        truck_number=canonical_doc.entities.get("truck", ""),
        truck_number_confidence=0.8 if canonical_doc.entities.get("truck", "") else 0.0,
        material=canonical_doc.entities.get("material", "") or (canonical_doc.line_items[0].description if canonical_doc.line_items else ""),
        material_confidence=0.75 if (canonical_doc.entities.get("material", "") or canonical_doc.line_items) else 0.0,
        destination=canonical_doc.entities.get("destination", "") or canonical_doc.entities.get("job_location", ""),
        destination_confidence=0.75 if (canonical_doc.entities.get("destination", "") or canonical_doc.entities.get("job_location", "")) else 0.0,
        status="review_pending",
        ocr_raw_text=raw_text,
        extracted_notes="",
        created_by=user_id,
    )


def _classify_material(material: str) -> str:
    """Return a broad material category string."""
    lowered = material.lower()
    if any(w in lowered for w in ("dirt", "soil", "clay", "fill")):
        return "earthwork"
    if any(w in lowered for w in ("asphalt", "milling", "paving")):
        return "asphalt"
    if any(w in lowered for w in ("concrete", "rebar")):
        return "concrete"
    if any(w in lowered for w in ("gravel", "aggregate", "stone", "rock", "rip rap", "base")):
        return "aggregate"
    if any(w in lowered for w in ("sand")):
        return "sand"
    if any(w in lowered for w in ("debris", "demo", "demolition", "waste", "trash")):
        return "debris"
    return "other" if material else ""


def _generate_issues(extraction: DocumentExtraction, *, profile_key: str = "ticket") -> list[dict]:
    """Return raw issue dicts for required/important fields that are empty or low-confidence."""
    issues: list[dict] = []
    required_fields = REQUIRED_FIELDS_BY_PROFILE.get(profile_key, REQUIRED_FIELDS_BY_PROFILE["ticket"])
    important_fields = IMPORTANT_FIELDS_BY_PROFILE.get(profile_key, IMPORTANT_FIELDS_BY_PROFILE["ticket"])

    # Required fields â†’ error severity
    for field_attr, field_label in required_fields:
        value = getattr(extraction, field_attr, "") or ""
        confidence = getattr(extraction, f"{field_attr}_confidence", 0.0) or 0.0
        if not value:
            issues.append({
                "issue_type": "missing_required",
                "field_name": field_attr,
                "severity": "warning" if profile_key == "estimator" and field_attr == "project_name" else "error",
                "message": f"Required field '{field_label}' was not detected in the document.",
                "suggested_value": "",
            })
        elif float(confidence) < 0.5:
            issues.append({
                "issue_type": "low_confidence",
                "field_name": field_attr,
                "severity": "warning" if profile_key == "estimator" and field_attr == "project_name" else "error",
                "message": f"'{field_label}' extracted with low confidence ({int(float(confidence) * 100)}%). Please verify.",
                "suggested_value": value,
            })

    # Important fields â†’ warning severity
    for field_attr, field_label in important_fields:
        value = getattr(extraction, field_attr, "") or ""
        if not value:
            issues.append({
                "issue_type": "missing_field",
                "field_name": field_attr,
                "severity": "warning",
                "message": f"'{field_label}' was not detected. Please fill in if known.",
                "suggested_value": "",
            })

    # Multi-document flag
    if extraction.is_multi_document:
        issues.append({
            "issue_type": "multi_document",
            "field_name": "document_count",
            "severity": "warning",
            "message": f"Multiple ticket blocks detected ({extraction.document_count}). Each block has been merged. Verify all data.",
            "suggested_value": str(extraction.document_count),
        })

    return issues


def _as_numeric(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


_AUTHORITY_RANK: dict[str, int] = {
    "addendum": 1,
    "document": 2,
    "geotech": 2,
    "estimate": 3,
    "quote": 4,
    "vendor": 4,
    "review": 5,
    "informational": 6,
}


def _build_field_level_discrepancies(
    canonical_payload: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    discrepancies: list[dict[str, object]] = []
    section_to_field: dict[str, str] = {
        "quantities": "quantity",
        "haul_costs": "haul_cost",
        "allowances": "allowance",
    }

    for section_name, field_key in section_to_field.items():
        entries = canonical_payload.get(section_name, [])
        numeric_candidates: list[dict[str, object]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            numeric_value = _as_numeric(entry.get("value"))
            if numeric_value is None:
                continue
            numeric_candidates.append(
                {
                    "value": numeric_value,
                    "unit": str(entry.get("unit") or ""),
                    "source_document_type": str(entry.get("source_document_type") or ""),
                    "original_source_text": str(entry.get("original_source_text") or ""),
                    "authority_level": str(entry.get("authority_level") or "informational"),
                    "confidence": float(entry.get("confidence") or 0.0),
                }
            )

        unique_values = {round(float(candidate["value"]), 6) for candidate in numeric_candidates}
        if len(unique_values) < 2:
            continue

        ranked = sorted(
            numeric_candidates,
            key=lambda candidate: (
                _AUTHORITY_RANK.get(str(candidate.get("authority_level") or "informational").lower(), 99),
                -float(candidate.get("confidence") or 0.0),
            ),
        )
        recommended = ranked[0]

        discrepancies.append(
            {
                "kind": f"{field_key}_conflict",
                "severity": "warning",
                "field_key": field_key,
                "message": (
                    f"Conflicting {field_key.replace('_', ' ')} values found across canonical evidence. "
                    f"Recommended value uses authority precedence ({recommended['authority_level']})."
                ),
                "rationale": (
                    f"Selected {recommended['value']} {recommended['unit']} from "
                    f"{recommended['source_document_type']} with authority_level={recommended['authority_level']}."
                ),
                "candidates": ranked,
                "recommended": recommended,
            }
        )

    return discrepancies


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Main service class
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class OCRExtractionService:
    "Creates DocumentExtraction records from existing IntakeItem OCR text."

    def __init__(self, db: Session, user_id: str, tenant_id: str):
        self.db = db
        self.user_id = user_id
        self.tenant_id = tenant_id

    def get_intake_item(self, intake_item_id: UUID) -> Optional[IntakeItem]:
        stmt = select(IntakeItem).where(
            IntakeItem.id == str(intake_item_id),
            IntakeItem.tenant_id == self.tenant_id,
        )
        return self.db.scalars(stmt).first()

    def has_existing_extraction(self, intake_item_id: UUID) -> Optional[DocumentExtraction]:
        """Return existing extraction for an intake item, if any."""
        stmt = select(DocumentExtraction).where(
            DocumentExtraction.intake_item_id == str(intake_item_id),
            DocumentExtraction.tenant_id == self.tenant_id,
        )
        return self.db.scalars(stmt).first()

    def _delete_normalized_canonical_rows(self, extraction_id: str) -> None:
        self.db.execute(
            delete(ExtractionCanonicalFact).where(
                ExtractionCanonicalFact.extraction_id == extraction_id,
                ExtractionCanonicalFact.tenant_id == self.tenant_id,
            )
        )
        self.db.execute(
            delete(ExtractionDiscrepancy).where(
                ExtractionDiscrepancy.extraction_id == extraction_id,
                ExtractionDiscrepancy.tenant_id == self.tenant_id,
            )
        )

    def _persist_normalized_canonical_rows(
        self,
        *,
        extraction_id: str,
        source_item_id: str,
        canonical_payload: dict[str, list[dict[str, object]]],
        canonical_discrepancies: list[dict[str, object]],
    ) -> None:
        fact_rows: list[ExtractionCanonicalFact] = []
        for section_name, entries in canonical_payload.items():
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                value = entry.get("value")
                unit = entry.get("unit")
                source_document_type = entry.get("source_document_type")
                evidence_text = entry.get("original_source_text")
                confidence = entry.get("confidence")
                authority_level = entry.get("authority_level")
                effective_date = entry.get("effective_date")
                page = entry.get("page")

                fact_rows.append(
                    ExtractionCanonicalFact(
                        id=str(uuid4()),
                        extraction_id=extraction_id,
                        tenant_id=self.tenant_id,
                        field_key=section_name,
                        value_text="" if value is None else str(value),
                        value_num=_as_numeric(value),
                        unit="" if unit is None else str(unit),
                        source_document_type="" if source_document_type is None else str(source_document_type),
                        source_item_id=source_item_id,
                        page=page if isinstance(page, int) else None,
                        evidence_text="" if evidence_text is None else str(evidence_text),
                        confidence=max(0.0, min(1.0, float(confidence or 0.0))),
                        authority_level="informational" if authority_level is None else str(authority_level),
                        effective_date="" if effective_date is None else str(effective_date),
                        created_by=self.user_id,
                    )
                )

        discrepancy_rows: list[ExtractionDiscrepancy] = []
        for discrepancy in canonical_discrepancies:
            if not isinstance(discrepancy, dict):
                continue
            discrepancy_rows.append(
                ExtractionDiscrepancy(
                    id=str(uuid4()),
                    extraction_id=extraction_id,
                    tenant_id=self.tenant_id,
                    discrepancy_key=str(discrepancy.get("kind") or "conflicting_evidence"),
                    severity=str(discrepancy.get("severity") or "warning"),
                    candidate_values_json=json.dumps(discrepancy.get("candidates") or []),
                    recommended_value_json=json.dumps(discrepancy.get("recommended") or {}),
                    rationale=str(discrepancy.get("message") or discrepancy.get("rationale") or ""),
                    created_by=self.user_id,
                )
            )

        if fact_rows:
            self.db.add_all(fact_rows)
        if discrepancy_rows:
            self.db.add_all(discrepancy_rows)

    def trigger_extraction_for_intake(
        self,
        intake_item_id: UUID,
        force: bool = False,
    ) -> DocumentExtraction:
        """
        Create a DocumentExtraction record from an intake item's OCR text.

        Args:
            intake_item_id: UUID of the IntakeItem to extract from.
            force: If True, re-extract even if a DocumentExtraction already exists.

        Returns:
            The created (or existing) DocumentExtraction.
        """
        # Check for existing extraction
        existing = self.has_existing_extraction(intake_item_id)
        if existing and not force:
            return existing

        # Load intake item
        item = self.get_intake_item(intake_item_id)
        if not item:
            raise ValueError(f"IntakeItem {intake_item_id} not found or not accessible")

        if not item.extracted_text:
            raise ValueError(
                f"IntakeItem {intake_item_id} has no OCR text. "
                "Ensure the file has been processed before triggering extraction."
            )

        canonical_doc = build_canonical_document(item)
        routing_scores = score_canonical_document(canonical_doc)

        # Run full field extraction using existing ticket_extractor
        candidates = extract_ticket_candidates(
            item.extracted_text,
            original_filename=item.original_filename or item.filename,
        )

        # Parse existing entities JSON as initial hints
        ocr_confidence: float = item.classification_confidence or 0.5
        if item.extracted_entities:
            try:
                existing_entities = json.loads(item.extracted_entities)
                # Merge as a low-priority fallback candidate
                if existing_entities and not candidates:
                    candidates = [existing_entities]
            except (json.JSONDecodeError, TypeError):
                pass

        if not candidates:
            # No fields extracted â€” create a blank extraction for manual entry
            candidates = [{}]

        use_estimator_profile = canonical_doc.document_type in ESTIMATOR_DOCUMENT_TYPES

        if use_estimator_profile:
            extraction = _map_canonical_to_extraction(
                canonical_doc=canonical_doc,
                routing_scores=routing_scores,
                raw_text=item.extracted_text,
                tenant_id=self.tenant_id,
                intake_item_id=str(intake_item_id),
                user_id=self.user_id,
            )
            issue_dicts = _generate_issues(extraction, profile_key="estimator")
        else:
            # Map to extraction model
            extraction, issue_dicts = _map_candidates_to_extraction(
                candidates=candidates,
                ocr_confidence=ocr_confidence,
                raw_text=item.extracted_text,
                tenant_id=self.tenant_id,
                intake_item_id=str(intake_item_id),
                user_id=self.user_id,
            )

        # If we're re-extracting, remove the old extraction first
        if existing and force:
            self._delete_normalized_canonical_rows(existing.id)
            self.db.delete(existing)
            self.db.flush()

        self.db.add(extraction)
        self.db.flush()

        if use_estimator_profile:
            canonical_payload = build_bid_package_payload(
                source_document_id=extraction.id,
                canonical_doc=canonical_doc,
            )
            canonical_discrepancies: list[dict[str, object]] = [
                {"kind": "conflicting_evidence", "message": message}
                for message in canonical_doc.conflicting_evidence
            ]
            canonical_discrepancies.extend(_build_field_level_discrepancies(canonical_payload))
            extraction.canonical_profile = "bid_package"
            extraction.canonical_revision = 1
            extraction.canonical_payload_json = json.dumps(canonical_payload)
            extraction.canonical_discrepancies_json = json.dumps(canonical_discrepancies)
            extraction.extracted_notes = json.dumps(
                {
                    "profile": "bid_package",
                    "canonical_payload": canonical_payload,
                    "canonical_discrepancies": canonical_discrepancies,
                    "supporting_evidence": list(canonical_doc.supporting_evidence),
                    "conflicting_evidence": list(canonical_doc.conflicting_evidence),
                }
            )
            self._persist_normalized_canonical_rows(
                extraction_id=extraction.id,
                source_item_id=str(intake_item_id),
                canonical_payload=canonical_payload,
                canonical_discrepancies=canonical_discrepancies,
            )
            self.db.flush()

        # Create OCR-level issue records (missing/low-confidence fields)
        for issue_dict in issue_dicts:
            issue = ExtractionIssue(
                id=str(uuid4()),
                extraction_id=extraction.id,
                tenant_id=self.tenant_id,
                issue_type=issue_dict["issue_type"],
                field_name=issue_dict["field_name"],
                severity=issue_dict["severity"],
                message=issue_dict["message"],
                suggested_value=issue_dict.get("suggested_value", ""),
                correction_source="ocr_extraction",
            )
            self.db.add(issue)

        self.db.flush()

        # Run validation rules (duplicate detection, overnight shift, weight sanity, etc.)
        from app.services.extraction_validation import ExtractionValidationService
        validator = ExtractionValidationService(self.db, self.tenant_id)
        validator.validate(extraction)

        return extraction


