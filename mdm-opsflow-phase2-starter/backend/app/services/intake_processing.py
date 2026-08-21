from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from uuid import uuid4

import fitz
from PIL import Image

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency fallback for local environments
    pytesseract = None

from app.models import IntakeStatus
from app.services.document_intake_router import route_ocr_document
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


def _build_stored_filename(original_filename: str, mime_type: str) -> str:
    safe_name = _sanitize_filename(original_filename)
    suffix = Path(safe_name).suffix.lower()

    if not suffix:
        mime_suffix_map = {
            "application/pdf": ".pdf",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "text/plain": ".txt",
            "text/csv": ".csv",
        }
        suffix = mime_suffix_map.get(mime_type, "")

    return f"{uuid4().hex[:16]}{suffix}"


def _extract_pdf_text(payload: bytes) -> str:
    try:
        with fitz.open(stream=payload, filetype="pdf") as document:
            page_text: list[str] = []
            for page in document:
                extracted = page.get_text("text").strip()
                if extracted:
                    page_text.append(extracted)
            text = "\n".join(page_text).strip()

        # Scanned PDFs have no embedded text layer — fall back to OCR on rendered images
        if not text and pytesseract is not None:
            with fitz.open(stream=payload, filetype="pdf") as document:
                ocr_pages: list[str] = []
                for page in document:
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    try:
                        img = Image.open(BytesIO(img_bytes))
                        page_ocr = pytesseract.image_to_string(img).strip()
                        if page_ocr:
                            ocr_pages.append(page_ocr)
                    except Exception:
                        pass
            text = "\n\n".join(ocr_pages).strip()

        return text
    except Exception:
        return ""


def _extract_image_text(payload: bytes) -> str:
    if pytesseract is None:
        return ""
    try:
        with Image.open(BytesIO(payload)) as image:
            return pytesseract.image_to_string(image).strip()
    except Exception:
        return ""


def _looks_like_text_payload(payload: bytes) -> bool:
    if not payload:
        return False
    try:
        decoded = payload.decode("utf-8")
    except UnicodeDecodeError:
        return False

    if not decoded.strip():
        return False

    printable_chars = sum(1 for char in decoded if char.isprintable() or char in {"\n", "\r", "\t"})
    return printable_chars / len(decoded) >= 0.9


def _extract_text(payload: bytes, mime_type: str) -> str:
    if mime_type.startswith("text/"):
        return payload.decode("utf-8", errors="replace").strip()
    if mime_type == "application/pdf":
        return _extract_pdf_text(payload)
    if mime_type.startswith("image/"):
        extracted = _extract_image_text(payload)
        if extracted:
            return extracted
        if _looks_like_text_payload(payload):
            return payload.decode("utf-8", errors="replace").strip()
        return ""
    if _looks_like_text_payload(payload):
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

    stored_filename = _build_stored_filename(original_filename, mime_type)
    absolute_file_path = tenant_path / stored_filename
    absolute_file_path.write_bytes(payload)

    content_hash = hashlib.sha256(payload).hexdigest()
    extracted_text = _extract_text(payload, mime_type)

    routing = route_ocr_document(extracted_text) if extracted_text else None
    entities, summary, confidence = extract_ticket_preview(extracted_text, original_filename=original_filename)
    legacy_ticket_detected = bool(entities)
    routing_detected_type = routing.document_type if routing else ""
    document_type = routing_detected_type if routing_detected_type and routing_detected_type != "unknown" else ("ticket" if legacy_ticket_detected else "general")
    if document_type == "haul_ticket":
        document_type = "ticket"
    if routing:
        routed_entities = routing.flattened_entities()
        routed_entities.update({key: str(value) for key, value in entities.items() if value})
        entities = routed_entities
        confidence = max(confidence, routing.classification_confidence)
        if not summary:
            summary_parts = [routing.document_type, routing.recommended_route]
            if routing.project.get("name"):
                summary_parts.append(str(routing.project["name"]))
            if routing.vendor.get("name"):
                summary_parts.append(str(routing.vendor["name"]))
            summary = "; ".join(summary_parts)

    routing_requires_review = bool(routing and routing.requires_human_review and not legacy_ticket_detected)
    needs_review = bool(extracted_text) and (confidence < 0.75 or routing_requires_review)
    review_reason = ""
    if needs_review:
        review_reason = routing.reason_for_review if routing and routing.reason_for_review else "Low extraction confidence; reviewer confirmation required."

    try:
        file_path = str(absolute_file_path.relative_to(_repo_root())).replace("\\", "/")
    except ValueError:
        file_path = str(absolute_file_path)

    return ProcessedIntakePayload(
        filename=stored_filename,
        original_filename=original_filename or stored_filename,
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
