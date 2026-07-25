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
