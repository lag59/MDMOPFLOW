from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

from app.models import IntakeStatus
from app.services.ticket_extractor import extract_ticket_preview


@dataclass(slots=True)
class ProcessedIntakePayload:
    filename: str
    original_filename: str
    file_path: str
    mime_type: str
    file_size_bytes: int
    content_hash: str
    document_type: str
    status: IntakeStatus
    processing_stage: str
    extracted_summary: str
    extracted_text: str
    extracted_entities: str
    ocr_status: str
    ai_status: str
    classification_confidence: float
    match_confidence: float
    needs_review: bool
    review_reason: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_storage_root() -> Path:
    return _repo_root() / "backend" / "storage" / "intake"


def _sanitize_filename(filename: str) -> str:
    candidate = filename.strip() or "upload.bin"
    candidate = candidate.replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "_", candidate)


def _extract_text(payload: bytes, mime_type: str) -> str:
    if mime_type.startswith("text/"):
        return payload.decode("utf-8", errors="replace").strip()
    return ""


def process_intake_upload(
    *,
    tenant_id: str,
    original_filename: str,
    mime_type: str,
    payload: bytes,
    storage_root: Path | None = None,
) -> ProcessedIntakePayload:
    root = storage_root or _default_storage_root()

    utc_now = datetime.utcnow()
    date_path = Path(f"{utc_now:%Y}") / f"{utc_now:%m}" / f"{utc_now:%d}"
    tenant_path = root / tenant_id / date_path
    tenant_path.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(original_filename)
    stored_filename = f"{uuid4().hex[:12]}_{safe_name}"
    absolute_file_path = tenant_path / stored_filename
    absolute_file_path.write_bytes(payload)

    content_hash = hashlib.sha256(payload).hexdigest()
    extracted_text = _extract_text(payload, mime_type)

    entities, summary, confidence = extract_ticket_preview(extracted_text)
    document_type = "ticket" if entities else "general"

    needs_review = bool(extracted_text) and confidence < 0.75
    review_reason = "Low extraction confidence; reviewer confirmation required." if needs_review else ""

    try:
        file_path = str(absolute_file_path.relative_to(_repo_root())).replace("\\", "/")
    except ValueError:
        file_path = str(absolute_file_path)

    return ProcessedIntakePayload(
        filename=safe_name,
        original_filename=original_filename or safe_name,
        file_path=file_path,
        mime_type=mime_type or "application/octet-stream",
        file_size_bytes=len(payload),
        content_hash=content_hash,
        document_type=document_type,
        status=IntakeStatus.QUEUED,
        processing_stage="queued",
        extracted_summary=summary,
        extracted_text=extracted_text,
        extracted_entities=json.dumps(entities),
        ocr_status="completed" if extracted_text else "pending",
        ai_status="completed" if summary else "pending",
        classification_confidence=confidence,
        match_confidence=confidence,
        needs_review=needs_review,
        review_reason=review_reason,
    )
