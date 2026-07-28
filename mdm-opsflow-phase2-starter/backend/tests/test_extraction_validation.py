"""Tests for the extraction validation engine."""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.extraction_validation import (
    ExtractionValidationService,
    _check_duplicate_ticket,
    _check_future_date,
    _check_hours_ceiling,
    _check_missing_time_pair,
    _check_negative_values,
    _check_overnight_shift,
    _check_stale_date,
    _check_weight_inversion,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

TENANT_ID = str(uuid4())


def _extraction(**kwargs) -> SimpleNamespace:
    """Create a minimal extraction namespace with sensible defaults."""
    defaults = dict(
        id=str(uuid4()),
        tenant_id=TENANT_ID,
        intake_item_id=str(uuid4()),
        document_type="ticket",
        document_type_confidence=0.85,
        company_name="Acme Hauling",
        ticket_number="TCK-001",
        ticket_number_confidence=0.90,
        driver_name="John Smith",
        truck_number="T-42",
        material="Dirt",
        material_confidence=0.80,
        destination="Job Site A",
        destination_confidence=0.75,
        weight_net_lbs=None,
        tons=None,
        load_count=None,
        total_hours_calculated=None,
        invoice_total=None,
        rate_per_ton=None,
        start_time=None,
        finish_time=None,
        ticket_date=None,
        status="review_pending",
        created_by=str(uuid4()),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _mock_db() -> MagicMock:
    db = MagicMock()
    db.scalars.return_value.first.return_value = None
    db.scalars.return_value.all.return_value = []
    return db


# ─────────────────────────────────────────────────────────────────────────────
# Rule: duplicate_ticket
# ─────────────────────────────────────────────────────────────────────────────

class TestDuplicateTicket:
    def test_no_issue_when_no_duplicate(self):
        db = _mock_db()
        extraction = _extraction(ticket_number="TCK-001")
        issues = _check_duplicate_ticket(extraction, db, TENANT_ID)
        assert issues == []

    def test_no_issue_when_ticket_number_empty(self):
        db = _mock_db()
        extraction = _extraction(ticket_number="")
        issues = _check_duplicate_ticket(extraction, db, TENANT_ID)
        assert issues == []

    def test_error_when_duplicate_distributed(self):
        existing = _extraction(id=str(uuid4()), ticket_number="TCK-001", status="distributed")
        db = _mock_db()
        db.scalars.return_value.first.return_value = existing

        extraction = _extraction(ticket_number="TCK-001")
        issues = _check_duplicate_ticket(extraction, db, TENANT_ID)

        assert len(issues) == 1
        assert issues[0]["issue_type"] == "duplicate_ticket"
        assert issues[0]["severity"] == "error"
        assert "TCK-001" in issues[0]["message"]


# ─────────────────────────────────────────────────────────────────────────────
# Rule: overnight_shift
# ─────────────────────────────────────────────────────────────────────────────

class TestOvernightShift:
    def test_no_issue_when_times_absent(self):
        extraction = _extraction()
        assert _check_overnight_shift(extraction) == []

    def test_no_issue_when_normal_shift(self):
        base = datetime(2026, 7, 27, 7, 0)
        extraction = _extraction(start_time=base, finish_time=base + timedelta(hours=8))
        assert _check_overnight_shift(extraction) == []

    def test_detects_and_fixes_overnight_shift(self):
        start = datetime(2026, 7, 27, 22, 0)
        finish = datetime(2026, 7, 27, 6, 0)  # next day 6am but same calendar date
        extraction = _extraction(start_time=start, finish_time=finish)

        issues = _check_overnight_shift(extraction)

        assert len(issues) == 1
        assert issues[0]["issue_type"] == "overnight_shift"
        assert issues[0]["severity"] == "warning"
        # finish_time should have been corrected to next day
        assert extraction.finish_time == datetime(2026, 7, 28, 6, 0)
        assert extraction.total_hours_calculated == 8.0

    def test_overnight_hours_calculation(self):
        start = datetime(2026, 7, 27, 23, 30)
        finish = datetime(2026, 7, 27, 1, 30)  # 2 hours later, crosses midnight
        extraction = _extraction(start_time=start, finish_time=finish)

        _check_overnight_shift(extraction)
        assert extraction.total_hours_calculated == 2.0


# ─────────────────────────────────────────────────────────────────────────────
# Rule: hours_ceiling
# ─────────────────────────────────────────────────────────────────────────────

class TestHoursCeiling:
    def test_no_issue_when_hours_absent(self):
        assert _check_hours_ceiling(_extraction()) == []

    def test_no_issue_for_normal_hours(self):
        assert _check_hours_ceiling(_extraction(total_hours_calculated=8.0)) == []

    def test_warning_for_hours_over_12(self):
        issues = _check_hours_ceiling(_extraction(total_hours_calculated=13.5))
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"

    def test_error_for_hours_over_16(self):
        issues = _check_hours_ceiling(_extraction(total_hours_calculated=17.0))
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"


# ─────────────────────────────────────────────────────────────────────────────
# Rule: weight_inversion
# ─────────────────────────────────────────────────────────────────────────────

class TestWeightInversion:
    def test_no_issue_when_weights_absent(self):
        assert _check_weight_inversion(_extraction()) == []

    def test_no_issue_when_consistent(self):
        # 20000 lbs = 10 tons exactly
        assert _check_weight_inversion(_extraction(weight_net_lbs=20000, tons=10.0)) == []

    def test_warning_when_tons_mismatches_net_lbs(self):
        # 20000 lbs = 10 tons, but tons says 15 → mismatch
        issues = _check_weight_inversion(_extraction(weight_net_lbs=20000, tons=15.0))
        assert len(issues) == 1
        assert issues[0]["issue_type"] == "weight_mismatch"
        assert issues[0]["severity"] == "warning"

    def test_no_issue_within_5_percent_tolerance(self):
        # 20000 lbs = 10 tons; 10.4 is within 5%
        assert _check_weight_inversion(_extraction(weight_net_lbs=20000, tons=10.4)) == []


# ─────────────────────────────────────────────────────────────────────────────
# Rule: negative_values
# ─────────────────────────────────────────────────────────────────────────────

class TestNegativeValues:
    def test_no_issues_for_positive_values(self):
        ext = _extraction(weight_net_lbs=5000, tons=2.5, load_count=5, total_hours_calculated=8.0)
        assert _check_negative_values(ext) == []

    def test_error_for_negative_tons(self):
        issues = _check_negative_values(_extraction(tons=-5.0))
        assert any(i["field_name"] == "tons" and i["severity"] == "error" for i in issues)

    def test_error_for_negative_invoice_total(self):
        issues = _check_negative_values(_extraction(invoice_total=-150.0))
        assert any(i["field_name"] == "invoice_total" for i in issues)

    def test_suggested_value_is_absolute(self):
        issues = _check_negative_values(_extraction(tons=-3.5))
        tons_issue = next(i for i in issues if i["field_name"] == "tons")
        assert tons_issue["suggested_value"] == "3.5"


# ─────────────────────────────────────────────────────────────────────────────
# Rule: future_date
# ─────────────────────────────────────────────────────────────────────────────

class TestFutureDate:
    def test_no_issue_when_date_absent(self):
        assert _check_future_date(_extraction()) == []

    def test_no_issue_for_today(self):
        assert _check_future_date(_extraction(ticket_date=datetime.utcnow())) == []

    def test_error_for_far_future_date(self):
        future = datetime.utcnow() + timedelta(days=30)
        issues = _check_future_date(_extraction(ticket_date=future))
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert issues[0]["issue_type"] == "future_date"


# ─────────────────────────────────────────────────────────────────────────────
# Rule: stale_date
# ─────────────────────────────────────────────────────────────────────────────

class TestStaleDate:
    def test_no_issue_for_recent_date(self):
        assert _check_stale_date(_extraction(ticket_date=datetime.utcnow())) == []

    def test_warning_for_date_over_1_year(self):
        old = datetime.utcnow() - timedelta(days=400)
        issues = _check_stale_date(_extraction(ticket_date=old))
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"
        assert issues[0]["issue_type"] == "stale_date"


# ─────────────────────────────────────────────────────────────────────────────
# Rule: missing_time_pair
# ─────────────────────────────────────────────────────────────────────────────

class TestMissingTimePair:
    def test_no_issue_when_both_absent(self):
        assert _check_missing_time_pair(_extraction()) == []

    def test_no_issue_when_both_present(self):
        now = datetime.utcnow()
        ext = _extraction(start_time=now, finish_time=now + timedelta(hours=8))
        assert _check_missing_time_pair(ext) == []

    def test_warning_when_only_start_present(self):
        issues = _check_missing_time_pair(_extraction(start_time=datetime.utcnow()))
        assert len(issues) == 1
        assert issues[0]["field_name"] == "finish_time"

    def test_warning_when_only_finish_present(self):
        issues = _check_missing_time_pair(_extraction(finish_time=datetime.utcnow()))
        assert len(issues) == 1
        assert issues[0]["field_name"] == "start_time"


# ─────────────────────────────────────────────────────────────────────────────
# ExtractionValidationService integration
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractionValidationService:
    def test_validate_clean_extraction_produces_no_issues(self):
        """A well-formed extraction with no anomalies should produce no validation issues."""
        db = _mock_db()
        service = ExtractionValidationService(db, TENANT_ID)

        extraction = _extraction(
            ticket_date=datetime.utcnow(),
            start_time=datetime(2026, 7, 27, 7, 0),
            finish_time=datetime(2026, 7, 27, 15, 0),
            total_hours_calculated=8.0,
            weight_net_lbs=20000,
            tons=10.0,
        )
        issues = service.validate(extraction)
        assert issues == []

    def test_validate_overnight_shift_auto_corrects(self):
        db = _mock_db()
        service = ExtractionValidationService(db, TENANT_ID)

        start = datetime(2026, 7, 27, 22, 0)
        finish = datetime(2026, 7, 27, 6, 0)
        extraction = _extraction(start_time=start, finish_time=finish)

        issues = service.validate(extraction)

        overnight = [i for i in issues if i.issue_type == "overnight_shift"]
        assert len(overnight) == 1
        assert extraction.finish_time == datetime(2026, 7, 28, 6, 0)

    def test_validate_persists_issues_to_db(self):
        db = _mock_db()
        service = ExtractionValidationService(db, TENANT_ID)

        extraction = _extraction(total_hours_calculated=20.0)  # exceeds ceiling
        service.validate(extraction)

        # db.add should have been called for the issue
        assert db.add.called

    def test_get_blocking_issues_filters_by_severity(self):
        db = _mock_db()

        error_issue = MagicMock()
        error_issue.severity = "error"
        error_issue.resolved = False

        warning_issue = MagicMock()
        warning_issue.severity = "warning"
        warning_issue.resolved = False

        db.scalars.return_value.all.return_value = [error_issue]
        service = ExtractionValidationService(db, TENANT_ID)

        extraction_id = uuid4()
        result = service.get_blocking_issues(extraction_id)
        assert result == [error_issue]
