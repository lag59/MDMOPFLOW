from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.services.intake_processing import process_intake_upload


def test_process_intake_upload_persists_file_and_hash(tmp_path: Path) -> None:
    payload = b"loader ticket sample"

    result = process_intake_upload(
        tenant_id="tenant-1",
        original_filename="ticket-1001.txt",
        mime_type="text/plain",
        payload=payload,
        storage_root=tmp_path,
    )

    written_path = Path(result.file_path)
    assert written_path.exists()
    assert written_path.read_bytes() == payload
    assert result.content_hash == hashlib.sha256(payload).hexdigest()
    assert result.file_size_bytes == len(payload)


def test_process_intake_upload_extracts_ticket_preview(tmp_path: Path) -> None:
    payload = (
        b"Ticket: TCK-1042\n"
        b"Driver: Jane Doe\n"
        b"Truck: Unit 24\n"
        b"Material: Gravel\n"
    )

    result = process_intake_upload(
        tenant_id="tenant-2",
        original_filename="dispatch-notes.txt",
        mime_type="text/plain",
        payload=payload,
        storage_root=tmp_path,
    )

    entities = json.loads(result.extracted_entities)
    assert result.document_type == "ticket"
    assert entities["ticket_number"] == "TCK-1042"
    assert "Ticket TCK-1042" in result.extracted_summary
    assert result.ocr_status == "completed"
    assert result.ai_status == "completed"


def test_process_intake_upload_uses_document_router_for_estimator_quote(tmp_path: Path) -> None:
    payload = (
        b"Hauling / Disposal Quote\n"
        b"Project: N. Ridge Commerce Pk Ph 2\n"
        b"Project Number: NRCP-PH2\n"
        b"Quote Number: HQ-24011\n"
        b"Assumed One-Way Distance: 16 miles\n"
        b"Truck Type Triaxle\n"
        b"Rate $125 per truck-hour\n"
    )

    result = process_intake_upload(
        tenant_id="tenant-3",
        original_filename="hauling-quote.txt",
        mime_type="text/plain",
        payload=payload,
        storage_root=tmp_path,
    )

    entities = json.loads(result.extracted_entities)
    assert result.document_type == "hauling_disposal_quote"
    assert result.classification_confidence >= 0.72
    assert entities["project_number"] == "NRCP-PH2"
    assert entities["reference_number"] == "HQ-24011"
    assert entities["recommended_route"] == "Estimator > Hauling > Vendor Quotes"


def test_process_intake_upload_routes_general_estimate_to_estimator(tmp_path: Path) -> None:
    payload = (
        b"Cost Estimate\n"
        b"Project: Riverbend Utility Extension\n"
        b"Estimate Number: EST-2026-014\n"
        b"Bid Form\n"
        b"Scope of Work: Earthwork and storm drainage\n"
        b"Cost Breakdown\n"
        b"Estimated Cost $1,245,000\n"
    )

    result = process_intake_upload(
        tenant_id="tenant-estimate",
        original_filename="estimate-review.txt",
        mime_type="text/plain",
        payload=payload,
        storage_root=tmp_path,
    )

    entities = json.loads(result.extracted_entities)
    assert result.document_type == "estimate"
    assert result.classification_confidence >= 0.72
    assert entities["document_type"] == "estimate"
    assert entities["recommended_route"] == "Estimator > Estimates > Review"


def test_process_intake_upload_keeps_legacy_ticket_type_for_haul_ticket(tmp_path: Path) -> None:
    payload = (
        b"HAUL TICKET\n"
        b"Ticket No. CH-004821\n"
        b"Date 08/11/2026\n"
        b"Truck T-17\n"
        b"Driver M. Sample\n"
        b"Material EXPORT SOIL\n"
        b"Load 18.6 tons\n"
    )

    result = process_intake_upload(
        tenant_id="tenant-4",
        original_filename="haul-ticket.txt",
        mime_type="text/plain",
        payload=payload,
        storage_root=tmp_path,
    )

    entities = json.loads(result.extracted_entities)
    assert result.document_type == "ticket"
    assert entities["document_type"] == "haul_ticket"
    assert entities["ticket_number"] == "CH-004821"
    assert entities["load_unit"] == "TON"
