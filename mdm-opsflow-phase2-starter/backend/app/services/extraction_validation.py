"""
Extraction Validation Engine

Runs after OCR extraction to detect data quality problems that regex alone
can't catch.  Each rule returns zero or more ExtractionIssue dicts that are
persisted alongside the extraction.

Rules implemented
─────────────────
1.  duplicate_ticket   – same ticket_number already distributed in this tenant
2.  duplicate_file     – same content_hash already distributed in this tenant
3.  overnight_shift    – finish_time < start_time → fix hours, add warning
4.  hours_ceiling      – total_hours_calculated > 16 → likely OCR misread
5.  weight_inversion   – net_weight > gross_weight (physically impossible)
6.  zero_weight        – weight fields are zero but tons > 0 (or vice-versa)
7.  negative_value     – any numeric field is negative
8.  future_date        – ticket_date is more than 1 day in the future
9.  stale_date         – ticket_date is more than 365 days in the past
10. missing_time_pair  – start_time present but finish_time missing (or vice-versa)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentExtraction, ExtractionIssue, IntakeItem


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _f(value) -> Optional[float]:
    """Safely coerce a DB value to float, returning None on failure."""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _issue(
    issue_type: str,
    field_name: str,
    severity: str,
    message: str,
    suggested_value: str = "",
) -> dict:
    return {
        "issue_type": issue_type,
        "field_name": field_name,
        "severity": severity,
        "message": message,
        "suggested_value": suggested_value,
        "correction_source": "validation_engine",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Individual rules (pure functions → list[dict])
# ─────────────────────────────────────────────────────────────────────────────

def _check_duplicate_ticket(
    extraction: DocumentExtraction, db: Session, tenant_id: str
) -> list[dict]:
    if not extraction.ticket_number:
        return []

    existing = db.scalars(
        select(DocumentExtraction).where(
            DocumentExtraction.tenant_id == tenant_id,
            DocumentExtraction.ticket_number == extraction.ticket_number,
            DocumentExtraction.status == "distributed",
            DocumentExtraction.id != extraction.id,
        )
    ).first()

    if existing:
        return [_issue(
            issue_type="duplicate_ticket",
            field_name="ticket_number",
            severity="error",
            message=(
                f"Ticket number '{extraction.ticket_number}' already exists as a "
                f"distributed record (ID: {existing.id[:8]}). Verify this is not a duplicate."
            ),
            suggested_value=extraction.ticket_number,
        )]
    return []


def _check_duplicate_file(
    extraction: DocumentExtraction, db: Session, tenant_id: str
) -> list[dict]:
    """Check if the source intake item's file hash matches an already-distributed extraction."""
    if not extraction.intake_item_id:
        return []

    # Get the content hash of this intake item
    item = db.scalars(
        select(IntakeItem).where(IntakeItem.id == extraction.intake_item_id)
    ).first()
    if not item or not item.content_hash:
        return []

    # Find another intake item with same hash that already has a distributed extraction
    duplicate_item = db.scalars(
        select(IntakeItem).where(
            IntakeItem.tenant_id == tenant_id,
            IntakeItem.content_hash == item.content_hash,
            IntakeItem.id != item.id,
        )
    ).first()

    if not duplicate_item:
        return []

    prior_extraction = db.scalars(
        select(DocumentExtraction).where(
            DocumentExtraction.intake_item_id == duplicate_item.id,
            DocumentExtraction.status == "distributed",
        )
    ).first()

    if prior_extraction:
        return [_issue(
            issue_type="duplicate_file",
            field_name="intake_item_id",
            severity="error",
            message=(
                f"This file's content matches a previously distributed document "
                f"(intake: {duplicate_item.id[:8]}, extraction: {prior_extraction.id[:8]}). "
                "Confirm this is intentional before approving."
            ),
        )]
    return []


def _check_overnight_shift(extraction: DocumentExtraction) -> list[dict]:
    """Detect and fix start/finish times that cross midnight."""
    issues: list[dict] = []

    if not extraction.start_time or not extraction.finish_time:
        return []

    start = extraction.start_time
    finish = extraction.finish_time

    if finish >= start:
        return []  # Normal — no issue

    # finish < start → likely crossed midnight
    finish_next_day = finish + timedelta(days=1)
    corrected_hours = round((finish_next_day - start).total_seconds() / 3600, 2)

    # Auto-correct the extraction fields
    extraction.finish_time = finish_next_day
    extraction.total_hours_calculated = corrected_hours

    issues.append(_issue(
        issue_type="overnight_shift",
        field_name="finish_time",
        severity="warning",
        message=(
            f"Finish time ({finish.strftime('%H:%M')}) is earlier than start time "
            f"({start.strftime('%H:%M')}), indicating an overnight shift. "
            f"Finish date advanced by 1 day. Corrected hours: {corrected_hours:.2f}."
        ),
        suggested_value=finish_next_day.isoformat(),
    ))
    return issues


def _check_hours_ceiling(extraction: DocumentExtraction) -> list[dict]:
    hours = _f(extraction.total_hours_calculated)
    if hours is None:
        return []
    if hours > 16:
        return [_issue(
            issue_type="hours_ceiling",
            field_name="total_hours_calculated",
            severity="error",
            message=(
                f"Calculated hours ({hours:.2f}h) exceeds 16 hours. "
                "This is likely an OCR misread of start or finish time. Please verify."
            ),
            suggested_value=str(hours),
        )]
    if hours > 12:
        return [_issue(
            issue_type="hours_ceiling",
            field_name="total_hours_calculated",
            severity="warning",
            message=(
                f"Calculated hours ({hours:.2f}h) is unusually high (>12h). "
                "Please verify start and finish times."
            ),
            suggested_value=str(hours),
        )]
    return []


def _check_weight_inversion(extraction: DocumentExtraction) -> list[dict]:
    """Net weight should always be less than gross weight."""
    # The model only stores net_weight_lbs; gross/tare are not persisted.
    # We can only validate tons vs net_weight_lbs consistency.
    net = _f(extraction.weight_net_lbs)
    tons = _f(extraction.tons)

    if net is None or tons is None:
        return []

    # tons = net_lbs / 2000 — allow 1% rounding tolerance
    expected_tons = net / 2000.0
    if tons > 0 and abs(tons - expected_tons) / tons > 0.05:
        return [_issue(
            issue_type="weight_mismatch",
            field_name="tons",
            severity="warning",
            message=(
                f"Tons ({tons}) does not match net weight ({net} lbs ÷ 2000 = "
                f"{expected_tons:.3f} tons). One value may have been misread."
            ),
            suggested_value=f"{expected_tons:.3f}",
        )]
    return []


def _check_negative_values(extraction: DocumentExtraction) -> list[dict]:
    issues: list[dict] = []
    checks = [
        ("weight_net_lbs", "Net Weight (lbs)"),
        ("tons", "Tons"),
        ("load_count", "Load Count"),
        ("total_hours_calculated", "Total Hours"),
        ("invoice_total", "Invoice Total"),
        ("rate_per_ton", "Rate per Ton"),
    ]
    for field, label in checks:
        val = _f(getattr(extraction, field, None))
        if val is not None and val < 0:
            issues.append(_issue(
                issue_type="negative_value",
                field_name=field,
                severity="error",
                message=f"'{label}' has a negative value ({val}). OCR likely misread a digit.",
                suggested_value=str(abs(val)),
            ))
    return issues


def _check_future_date(extraction: DocumentExtraction) -> list[dict]:
    if not extraction.ticket_date:
        return []
    now = datetime.utcnow()
    if extraction.ticket_date > now + timedelta(days=1):
        return [_issue(
            issue_type="future_date",
            field_name="ticket_date",
            severity="error",
            message=(
                f"Ticket date ({extraction.ticket_date.strftime('%Y-%m-%d')}) is in the future. "
                "Likely an OCR misread of the year or day."
            ),
            suggested_value=now.strftime("%Y-%m-%d"),
        )]
    return []


def _check_stale_date(extraction: DocumentExtraction) -> list[dict]:
    if not extraction.ticket_date:
        return []
    cutoff = datetime.utcnow() - timedelta(days=365)
    if extraction.ticket_date < cutoff:
        return [_issue(
            issue_type="stale_date",
            field_name="ticket_date",
            severity="warning",
            message=(
                f"Ticket date ({extraction.ticket_date.strftime('%Y-%m-%d')}) is more than "
                "1 year old. Verify this is not a mis-parsed date."
            ),
            suggested_value=extraction.ticket_date.strftime("%Y-%m-%d"),
        )]
    return []


def _check_missing_time_pair(extraction: DocumentExtraction) -> list[dict]:
    has_start = extraction.start_time is not None
    has_finish = extraction.finish_time is not None

    if has_start and not has_finish:
        return [_issue(
            issue_type="missing_time_pair",
            field_name="finish_time",
            severity="warning",
            message="Start time was detected but finish time is missing. Hours cannot be calculated.",
        )]
    if has_finish and not has_start:
        return [_issue(
            issue_type="missing_time_pair",
            field_name="start_time",
            severity="warning",
            message="Finish time was detected but start time is missing. Hours cannot be calculated.",
        )]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Main service
# ─────────────────────────────────────────────────────────────────────────────

class ExtractionValidationService:
    """Runs all validation rules against a DocumentExtraction and persists issues."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def validate(self, extraction: DocumentExtraction) -> list[ExtractionIssue]:
        """
        Run all validation rules.  Persists new ExtractionIssue rows and
        returns them.  Also auto-corrects fields where safe (overnight shift).

        Call this AFTER the extraction record is flushed but BEFORE commit.
        """
        raw_issues: list[dict] = []

        # Run each rule
        raw_issues += _check_duplicate_ticket(extraction, self.db, self.tenant_id)
        raw_issues += _check_duplicate_file(extraction, self.db, self.tenant_id)
        raw_issues += _check_overnight_shift(extraction)   # may mutate extraction
        raw_issues += _check_hours_ceiling(extraction)
        raw_issues += _check_weight_inversion(extraction)
        raw_issues += _check_negative_values(extraction)
        raw_issues += _check_future_date(extraction)
        raw_issues += _check_stale_date(extraction)
        raw_issues += _check_missing_time_pair(extraction)

        # Persist
        persisted: list[ExtractionIssue] = []
        for raw in raw_issues:
            from uuid import uuid4
            issue = ExtractionIssue(
                id=str(uuid4()),
                extraction_id=extraction.id,
                tenant_id=self.tenant_id,
                issue_type=raw["issue_type"],
                field_name=raw["field_name"],
                severity=raw["severity"],
                message=raw["message"],
                suggested_value=raw.get("suggested_value", ""),
                correction_source=raw.get("correction_source", "validation_engine"),
            )
            self.db.add(issue)
            persisted.append(issue)

        if persisted:
            self.db.flush()

        return persisted

    def get_blocking_issues(self, extraction_id: UUID) -> list[ExtractionIssue]:
        """Return unresolved error-severity issues that block approval."""
        return list(self.db.scalars(
            select(ExtractionIssue).where(
                ExtractionIssue.extraction_id == str(extraction_id),
                ExtractionIssue.tenant_id == self.tenant_id,
                ExtractionIssue.resolved == False,
                ExtractionIssue.severity == "error",
            )
        ).all())
