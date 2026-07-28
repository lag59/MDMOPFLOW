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

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentExtraction, ExtractionIssue, IntakeItem
from app.services.ticket_extractor import extract_ticket_candidates


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Required / important field definitions
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Fields that MUST be present for approval â€” missing â†’ error issue
REQUIRED_FIELDS: list[tuple[str, str]] = [
    ("ticket_number", "Ticket Number"),
    ("driver_name", "Driver Name"),
    ("material", "Material"),
]

# Fields we want but aren't blockers â€” missing â†’ warning issue
IMPORTANT_FIELDS: list[tuple[str, str]] = [
    ("truck_number", "Truck Number"),
    ("destination", "Destination / Dump Site"),
    ("job_location", "Job Location"),
    ("company_name", "Hauling Company"),
    ("ticket_date", "Ticket Date"),
]

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
    issues = _generate_issues(extraction)

    return extraction, issues


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


def _generate_issues(extraction: DocumentExtraction) -> list[dict]:
    """Return raw issue dicts for required/important fields that are empty or low-confidence."""
    issues: list[dict] = []

    # Required fields â†’ error severity
    for field_attr, field_label in REQUIRED_FIELDS:
        value = getattr(extraction, field_attr, "") or ""
        confidence = getattr(extraction, f"{field_attr}_confidence", 0.0) or 0.0
        if not value:
            issues.append({
                "issue_type": "missing_required",
                "field_name": field_attr,
                "severity": "error",
                "message": f"Required field '{field_label}' was not detected in the document.",
                "suggested_value": "",
            })
        elif float(confidence) < 0.5:
            issues.append({
                "issue_type": "low_confidence",
                "field_name": field_attr,
                "severity": "error",
                "message": f"'{field_label}' extracted with low confidence ({int(float(confidence) * 100)}%). Please verify.",
                "suggested_value": value,
            })

    # Important fields â†’ warning severity
    for field_attr, field_label in IMPORTANT_FIELDS:
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
            self.db.delete(existing)
            self.db.flush()

        self.db.add(extraction)
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


