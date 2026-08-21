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
        b"Work includes earthwork and storm drainage\n"
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


def test_process_intake_upload_treats_generic_quote_as_estimate(tmp_path: Path) -> None:
    payload = (
        b"Quote\n"
        b"Project: Riverbend Utility Extension\n"
        b"Quote Number: Q-2026-014\n"
        b"Proposal Total: $1,245,000\n"
        b"Work includes earthwork and storm drainage\n"
    )

    result = process_intake_upload(
        tenant_id="tenant-quote",
        original_filename="quote.txt",
        mime_type="text/plain",
        payload=payload,
        storage_root=tmp_path,
    )

    entities = json.loads(result.extracted_entities)
    assert result.document_type == "generic_quote"
    assert result.classification_confidence >= 0.72
    assert entities["document_type"] == "generic_quote"
    assert entities["reference_number"] == "Q-2026-014"
    assert entities["recommended_route"] == "Estimator > Estimates > Review"


def test_process_intake_upload_routes_contract_to_portfolio_review(tmp_path: Path) -> None:
    payload = (
        b"Construction Contract\n"
        b"Project: Riverbend Utility Extension\n"
        b"Contract Number: CON-2026-044\n"
        b"Owner-Contractor Agreement\n"
        b"Contract Sum: $4,200,000\n"
        b"Notice to Proceed: 09/01/2026\n"
        b"Substantial Completion: 180 days\n"
        b"Retainage: 5%\n"
    )

    result = process_intake_upload(
        tenant_id="tenant-contract",
        original_filename="contract.txt",
        mime_type="text/plain",
        payload=payload,
        storage_root=tmp_path,
    )

    entities = json.loads(result.extracted_entities)
    assert result.document_type == "contract"
    assert result.classification_confidence >= 0.72
    assert entities["document_type"] == "contract"
    assert entities["reference_number"] == "CON-2026-044"
    assert entities["recommended_route"] == "Projects > Contracts > Review"


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


def test_image_upload_preserves_source_ticket_number_metadata(tmp_path: Path) -> None:
    payload = (
        b"HAUL TICKET\n"
        b"Ticket # 10984\n"
        b"Date: 05/28/2026\n"
        b"Driver: Christon Bush\n"
        b"Truck: DL5\n"
        b"Jobsite: Buffaloe Reserve\n"
        b"Material: 57 stone\n"
    )

    result = process_intake_upload(
        tenant_id="tenant-image-source",
        original_filename="IMG_10984.jpeg",
        mime_type="image/jpeg",
        payload=payload,
        storage_root=tmp_path,
    )

    entities = json.loads(result.extracted_entities)
    assert result.mime_type == "image/jpeg"
    assert result.filename.endswith(".jpeg") or result.filename.endswith(".jpg")
    assert result.document_type == "ticket"
    assert entities["ticket_number"] == "10984"
    assert entities["ticket_number_source"] == "source_document"
    assert entities["ticket_number_generated"] is False


def test_png_image_upload_generates_missing_ticket_number(tmp_path: Path) -> None:
    payload = (
        b"LOAD TICKET\n"
        b"Date: 05/28/2026\n"
        b"Driver: Christon Bush\n"
        b"Truck: DL5\n"
        b"Jobsite: Buffaloe Reserve\n"
        b"Material: 57 stone\n"
    )

    result = process_intake_upload(
        tenant_id="tenant-image-generated",
        original_filename="IMG_1396.png",
        mime_type="image/png",
        payload=payload,
        storage_root=tmp_path,
    )

    entities = json.loads(result.extracted_entities)
    assert result.document_type == "ticket"
    assert entities["ticket_number"] == "BUSH-DL5-BUFFALOE-RESERVE-20260528"
    assert entities["ticket_number_source"] == "system_generated"
    assert entities["ticket_number_generated"] is True
    assert entities["ticket_number_generation_version"] == "driver-truck-jobsite-date-v1"


def test_jpg_image_upload_uses_unknown_placeholder_only_in_generated_identifier(tmp_path: Path) -> None:
    payload = (
        b"LOAD TICKET\n"
        b"Date: 05/28/2026\n"
        b"Driver: Christon Bush\n"
        b"Jobsite: Buffaloe Reserve\n"
        b"Material: 57 stone\n"
    )

    result = process_intake_upload(
        tenant_id="tenant-image-missing-truck",
        original_filename="IMG_1397.jpg",
        mime_type="image/jpg",
        payload=payload,
        storage_root=tmp_path,
    )

    entities = json.loads(result.extracted_entities)
    assert entities["ticket_number"] == "BUSH-UNKNOWNTRUCK-BUFFALOE-RESERVE-20260528"
    assert "truck" not in entities
    assert result.needs_review is True


def test_image_load_count_disagreement_requires_review(tmp_path: Path) -> None:
    payload = (
        b"LOAD TICKET\n"
        b"Date: 05/28/2026\n"
        b"Driver: Christon Bush\n"
        b"Truck: DL5\n"
        b"Jobsite: Buffaloe Reserve\n"
        b"Material: 57 stone\n"
        b"Total Loads: 11\n"
        b"Marked Loads: 10\n"
    )

    result = process_intake_upload(
        tenant_id="tenant-image-load-conflict",
        original_filename="IMG_1398.png",
        mime_type="image/png",
        payload=payload,
        storage_root=tmp_path,
    )

    entities = json.loads(result.extracted_entities)
    assert entities["number_of_loads"] == "11"
    assert entities["counted_loads"] == "10"
    assert result.needs_review is True
    assert "Load count conflict" in result.review_reason
