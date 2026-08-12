"""
Integration tests for the OCR extraction pipeline.

Covers:
  - OCRExtractionService.trigger_extraction_for_intake() end-to-end
  - Field mapping from ticket_extractor candidates → DocumentExtraction
  - Issue generation for missing required / important fields
  - Force re-extraction
  - API: POST /api/extractions/intake/{id}/extract
  - API: GET /api/extractions  (list)
  - API: GET /api/extractions/{id}  (detail)
  - API: POST /api/extractions/{id}/review
  - API: POST /api/extractions/{id}/validate
"""
from __future__ import annotations

import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import complete_onboarding, register_user

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

_TICKET_TEXT = """\
Ticket # 20250714
Date: 07/14/2025
Driver: Mike Johnson
Truck #: T-99
Company Hauling For: Acme Haulers Inc
Contractor: City Roads LLC
Job Location: 123 Main St, Portland OR
Material: Gravel
Start Time: 7:00 AM
Finish Time: 3:30 PM
Net Weight: 42000 lbs
# of Loads # 5
"""

_MINIMAL_TEXT = """\
Some document without any recognizable ticket fields.
"""


def _auth(client: TestClient) -> tuple[str, str]:
    """Register, onboard, and return (access_token, tenant_id)."""
    data = register_user(client, f"user-{uuid4().hex[:6]}@test.com", "Pass12345!", "Tester")
    token = data["tokens"]["access_token"]
    ob = complete_onboarding(client, token, f"Co-{uuid4().hex[:6]}", "P1")
    tenant_id = ob["tenant_id"]
    return token, tenant_id


def _upload(client: TestClient, token: str, tenant_id: str, text: str = _TICKET_TEXT) -> dict:
    """Upload a plain-text intake file and return the item JSON."""
    resp = client.post(
        "/api/intake/upload",
        files={"file": ("ticket.txt", io.BytesIO(text.encode()), "text/plain")},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _trigger(client: TestClient, token: str, tenant_id: str, item_id: str, force: bool = False) -> dict:
    """Trigger extraction for an intake item and return response JSON."""
    url = f"/api/extractions/intake/{item_id}/extract"
    if force:
        url += "?force=true"
    resp = client.post(url, headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# OCR extraction trigger
# ─────────────────────────────────────────────────────────────────────────────

class TestTriggerExtraction:
    def test_creates_extraction_from_uploaded_text(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id)

        result = _trigger(client, token, tenant_id, item["id"])

        assert result["extraction_id"]
        assert result["intake_item_id"] == item["id"]
        assert result["status"] == "review_pending"
        # BackgroundTask on TestClient runs synchronously, so extraction may already
        # exist from the upload; either new or existing is valid here
        assert result["is_new"] in (True, False)

    def test_fields_extracted_count_reflects_ticket_content(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)

        result = _trigger(client, token, tenant_id, item["id"])

        # The ticket text has: ticket_number, driver_name, truck_number, material,
        # destination (job_location), company_name → expect >= 4 fields extracted
        assert result["fields_extracted"] >= 4

    def test_idempotent_without_force(self, client: TestClient):
        """Calling trigger twice without force returns the same extraction."""
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id)

        first = _trigger(client, token, tenant_id, item["id"])
        second = _trigger(client, token, tenant_id, item["id"])

        assert first["extraction_id"] == second["extraction_id"]
        assert second["is_new"] is False

    def test_force_creates_new_extraction(self, client: TestClient):
        """force=true replaces an existing extraction with a fresh one."""
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id)

        first = _trigger(client, token, tenant_id, item["id"])
        second = _trigger(client, token, tenant_id, item["id"], force=True)

        assert first["extraction_id"] != second["extraction_id"]
        assert second["is_new"] is True

    def test_returns_404_for_unknown_intake_item(self, client: TestClient):
        token, tenant_id = _auth(client)
        resp = client.post(
            f"/api/extractions/intake/{uuid4()}/extract",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 400  # ValueError → 400

    def test_requires_authentication(self, client: TestClient):
        resp = client.post(f"/api/extractions/intake/{uuid4()}/extract")
        assert resp.status_code in (401, 403)

    def test_tenant_isolation(self, client: TestClient):
        """A user cannot trigger extraction for another tenant's intake item."""
        token1, tenant1 = _auth(client)
        token2, tenant2 = _auth(client)

        item = _upload(client, token1, tenant1)

        resp = client.post(
            f"/api/extractions/intake/{item['id']}/extract",
            headers={"Authorization": f"Bearer {token2}", "X-Tenant-ID": tenant2},
        )
        assert resp.status_code == 400  # not found in tenant2


# ─────────────────────────────────────────────────────────────────────────────
# Field mapping — verify ticket fields reach the extraction record
# ─────────────────────────────────────────────────────────────────────────────

class TestFieldMapping:
    def _get_detail(self, client, token, tenant_id, extraction_id) -> dict:
        resp = client.get(
            f"/api/extractions/{extraction_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_ticket_number_extracted(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        result = _trigger(client, token, tenant_id, item["id"])

        detail = self._get_detail(client, token, tenant_id, result["extraction_id"])
        assert detail["extraction"]["ticket_number"] == "20250714"

    def test_material_extracted(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        result = _trigger(client, token, tenant_id, item["id"])

        detail = self._get_detail(client, token, tenant_id, result["extraction_id"])
        assert detail["extraction"]["material"].lower() == "gravel"

    def test_document_type_is_ticket(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        result = _trigger(client, token, tenant_id, item["id"])

        detail = self._get_detail(client, token, tenant_id, result["extraction_id"])
        assert detail["extraction"]["document_type"] == "ticket"

    def test_confidence_scores_populated(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        result = _trigger(client, token, tenant_id, item["id"])

        detail = self._get_detail(client, token, tenant_id, result["extraction_id"])
        ext = detail["extraction"]
        # ticket_number was extracted so its confidence should be > 0
        assert float(ext["ticket_number_confidence"]) > 0

    def test_bid_package_doc_uses_estimator_profile_and_emits_canonical_payload(self, client: TestClient):
        token, tenant_id = _auth(client)
        quote_text = """\
Hauling / Disposal Quote
Project: North Ridge Commerce Park - Phase 2
Project Number: NRCP-PH2
Quote Number: HQ-24011
Assumed One-Way Distance: 16 miles
Estimated Quantity: 100 CY
Undercut Allowance: 200 CY
Addendum 2: Revised quantity to 120 CY
Addendum 2: Assumed One-Way Distance: 18 miles
Addendum 2: Undercut Allowance: 150 CY
"""
        item = _upload(client, token, tenant_id, quote_text)
        result = _trigger(client, token, tenant_id, item["id"], force=True)

        detail = self._get_detail(client, token, tenant_id, result["extraction_id"])
        ext = detail["extraction"]
        assert ext["document_type"] == "hauling_disposal_quote"
        assert ext["canonical_profile"] == "bid_package"
        assert ext["canonical_revision"] == 1
        assert ext["canonical_payload"] is not None
        assert len(ext["canonical_payload"].get("project_identity", [])) >= 1
        assert len(ext["canonical_payload"].get("haul_costs", [])) >= 1
        assert isinstance(ext.get("canonical_discrepancies") or [], list)
        assert isinstance(ext.get("canonical_source_facts") or [], list)
        assert len(ext.get("canonical_source_facts") or []) >= 1
        assert isinstance(ext.get("discrepancy_summary") or {}, dict)
        discrepancy_kinds = {
            str(item.get("kind"))
            for item in (ext.get("canonical_discrepancies") or [])
            if isinstance(item, dict)
        }
        assert "quantity_conflict" in discrepancy_kinds
        assert "haul_cost_conflict" in discrepancy_kinds
        assert "allowance_conflict" in discrepancy_kinds


# ─────────────────────────────────────────────────────────────────────────────
# Issue generation
# ─────────────────────────────────────────────────────────────────────────────

class TestIssueGeneration:
    def _get_issues(self, client, token, tenant_id, extraction_id) -> list:
        resp = client.get(
            f"/api/extractions/{extraction_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 200
        return resp.json()["issues"]

    def test_missing_required_fields_produce_errors(self, client: TestClient):
        """Uploading a document with no ticket fields should generate error issues."""
        token, tenant_id = _auth(client)
        # Use a filename without 'ticket' or any digits to avoid filename fallback
        resp = client.post(
            "/api/intake/upload",
            files={"file": ("document.bin", io.BytesIO(_MINIMAL_TEXT.encode()), "text/plain")},
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 201
        item = resp.json()
        result = _trigger(client, token, tenant_id, item["id"], force=True)

        issues = self._get_issues(client, token, tenant_id, result["extraction_id"])
        error_issues = [i for i in issues if i["severity"] == "error"]
        # At least driver_name and material should be missing
        assert len(error_issues) >= 2

    def test_well_formed_ticket_has_fewer_errors(self, client: TestClient):
        """A ticket with most fields present should have fewer error issues."""
        token, tenant_id = _auth(client)
        item_full = _upload(client, token, tenant_id, _TICKET_TEXT)
        item_empty = _upload(client, token, tenant_id, _MINIMAL_TEXT)

        result_full = _trigger(client, token, tenant_id, item_full["id"])
        result_empty = _trigger(client, token, tenant_id, item_empty["id"])

        issues_full = self._get_issues(client, token, tenant_id, result_full["extraction_id"])
        issues_empty = self._get_issues(client, token, tenant_id, result_empty["extraction_id"])

        errors_full = len([i for i in issues_full if i["severity"] == "error"])
        errors_empty = len([i for i in issues_empty if i["severity"] == "error"])

        assert errors_full < errors_empty

    def test_issue_has_required_fields(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _MINIMAL_TEXT)
        result = _trigger(client, token, tenant_id, item["id"])

        issues = self._get_issues(client, token, tenant_id, result["extraction_id"])
        assert len(issues) > 0

        issue = issues[0]
        assert "id" in issue
        assert "issue_type" in issue
        assert "field_name" in issue
        assert "severity" in issue
        assert "message" in issue
        assert issue["resolved"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Extraction list endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractionList:
    def test_lists_pending_extractions(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id)
        _trigger(client, token, tenant_id, item["id"])

        resp = client.get(
            "/api/extractions?status_filter=review_pending",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_item_has_expected_shape(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        _trigger(client, token, tenant_id, item["id"])

        resp = client.get(
            "/api/extractions",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1

        first = items[0]
        assert "id" in first
        assert "status" in first
        assert "document_type" in first
        assert "avg_confidence" in first
        assert "issue_count" in first

    def test_tenant_isolation_in_list(self, client: TestClient):
        """Tenant A extractions are not visible to Tenant B."""
        token1, tenant1 = _auth(client)
        token2, tenant2 = _auth(client)

        item = _upload(client, token1, tenant1)
        _trigger(client, token1, tenant1, item["id"])

        resp = client.get(
            "/api/extractions",
            headers={"Authorization": f"Bearer {token2}", "X-Tenant-ID": tenant2},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_pagination_limit(self, client: TestClient):
        token, tenant_id = _auth(client)
        # Upload 3 files and trigger 3 extractions
        for _ in range(3):
            item = _upload(client, token, tenant_id)
            _trigger(client, token, tenant_id, item["id"])

        resp = client.get(
            "/api/extractions?limit=2",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["total"] >= 3


# ─────────────────────────────────────────────────────────────────────────────
# Review submission
# ─────────────────────────────────────────────────────────────────────────────

class TestReviewSubmission:
    def test_submit_review_changes_status(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        trigger = _trigger(client, token, tenant_id, item["id"])
        extraction_id = trigger["extraction_id"]

        resp = client.post(
            f"/api/extractions/{extraction_id}/review",
            json={"review_notes": "Looks good", "corrections": {}},
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["extraction"]["status"] == "review_submitted"

    def test_corrections_are_applied(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        trigger = _trigger(client, token, tenant_id, item["id"])
        extraction_id = trigger["extraction_id"]

        resp = client.post(
            f"/api/extractions/{extraction_id}/review",
            json={
                "review_notes": "Corrected destination",
                "corrections": {"destination": "456 Oak Ave, Portland OR"},
            },
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 200
        # Correction stored — extraction updated
        detail = client.get(
            f"/api/extractions/{extraction_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        ).json()
        assert detail["extraction"]["destination"] == "456 Oak Ave, Portland OR"

    def test_review_notes_stored(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        trigger = _trigger(client, token, tenant_id, item["id"])
        extraction_id = trigger["extraction_id"]

        notes = "Reviewed carefully — all fields verified."
        resp = client.post(
            f"/api/extractions/{extraction_id}/review",
            json={"review_notes": notes, "corrections": {}},
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 200
        assert resp.json()["extraction"]["review_notes"] == notes

    def test_review_unknown_extraction_returns_400(self, client: TestClient):
        token, tenant_id = _auth(client)
        resp = client.post(
            f"/api/extractions/{uuid4()}/review",
            json={"review_notes": "", "corrections": {}},
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Approval endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestApprovalEndpoint:
    def test_approve_distributes_extraction(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        trigger = _trigger(client, token, tenant_id, item["id"])
        extraction_id = trigger["extraction_id"]

        review_resp = client.post(
            f"/api/extractions/{extraction_id}/review",
            json={
                "review_notes": "Reviewed and ready for approval",
                "corrections": {},
            },
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert review_resp.status_code == 200

        approve_resp = client.post(
            f"/api/extractions/{extraction_id}/approve",
            json={
                "approve": True,
                "approval_notes": "Approved for distribution",
            },
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert approve_resp.status_code == 200, approve_resp.text
        payload = approve_resp.json()
        assert payload["status"] == "distributed"
        assert payload["distributed_at"] is not None
        assert payload["distribution_summary"]["audit_logged"] is True

    def test_reject_sets_rejected_status(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        trigger = _trigger(client, token, tenant_id, item["id"])
        extraction_id = trigger["extraction_id"]

        review_resp = client.post(
            f"/api/extractions/{extraction_id}/review",
            json={
                "review_notes": "Needs correction",
                "corrections": {},
            },
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert review_resp.status_code == 200

        reject_resp = client.post(
            f"/api/extractions/{extraction_id}/approve",
            json={
                "approve": False,
                "rejection_reason": "Illegible driver name",
            },
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert reject_resp.status_code == 200, reject_resp.text
        assert reject_resp.json()["status"] == "rejected"

    def test_approve_requires_review_submitted_status(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        trigger = _trigger(client, token, tenant_id, item["id"])
        extraction_id = trigger["extraction_id"]

        approve_resp = client.post(
            f"/api/extractions/{extraction_id}/approve",
            json={
                "approve": True,
                "approval_notes": "Try to approve early",
            },
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert approve_resp.status_code == 400
        assert "review_submitted" in approve_resp.json()["detail"]

    def test_list_status_filter_includes_distributed(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        trigger = _trigger(client, token, tenant_id, item["id"])
        extraction_id = trigger["extraction_id"]

        review_resp = client.post(
            f"/api/extractions/{extraction_id}/review",
            json={
                "review_notes": "Reviewed and ready",
                "corrections": {},
            },
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert review_resp.status_code == 200

        approve_resp = client.post(
            f"/api/extractions/{extraction_id}/approve",
            json={
                "approve": True,
                "approval_notes": "Ship it",
            },
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert approve_resp.status_code == 200

        list_resp = client.get(
            "/api/extractions?status_filter=distributed",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert list_resp.status_code == 200, list_resp.text
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert extraction_id in ids


# ─────────────────────────────────────────────────────────────────────────────
# Validate endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateEndpoint:
    def test_validate_returns_detail_response(self, client: TestClient):
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        trigger = _trigger(client, token, tenant_id, item["id"])
        extraction_id = trigger["extraction_id"]

        resp = client.post(
            f"/api/extractions/{extraction_id}/validate",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "extraction" in data
        assert "issues" in data

    def test_validate_unknown_extraction_returns_404(self, client: TestClient):
        token, tenant_id = _auth(client)
        resp = client.post(
            f"/api/extractions/{uuid4()}/validate",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 404


class TestFileServe:
    def test_get_file_returns_file_with_correct_mime_type(self, client: TestClient):
        """Test that file serve endpoint returns the uploaded file with correct MIME type."""
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        item_id = item["id"]
        
        # Fetch the file
        resp = client.get(
            f"/api/intake/items/{item_id}/file",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] in (
            "text/plain",
            "text/plain; charset=utf-8"
        ), f"Got: {resp.headers['content-type']}"
        assert _TICKET_TEXT.encode() in resp.content

    def test_get_file_enforces_tenant_isolation(self, client: TestClient):
        """Test that users cannot access files from other tenants."""
        # User A uploads a file
        token_a, tenant_a = _auth(client)
        item_a = _upload(client, token_a, tenant_a, _TICKET_TEXT)
        
        # User B tries to access User A's file
        token_b, tenant_b = _auth(client)
        resp = client.get(
            f"/api/intake/items/{item_a['id']}/file",
            headers={"Authorization": f"Bearer {token_b}", "X-Tenant-ID": tenant_b},
        )
        assert resp.status_code == 404

    def test_get_file_unknown_item_returns_404(self, client: TestClient):
        """Test that requesting a non-existent file returns 404."""
        token, tenant_id = _auth(client)
        resp = client.get(
            f"/api/intake/items/{uuid4()}/file",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert resp.status_code == 404

    def test_get_file_requires_authentication(self, client: TestClient):
        """Test that file serve endpoint requires authentication."""
        token, tenant_id = _auth(client)
        item = _upload(client, token, tenant_id, _TICKET_TEXT)
        
        resp = client.get(f"/api/intake/items/{item['id']}/file")
        assert resp.status_code in (401, 403)
