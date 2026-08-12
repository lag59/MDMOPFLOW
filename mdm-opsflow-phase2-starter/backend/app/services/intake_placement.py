from __future__ import annotations

import json
from dataclasses import dataclass

from app.models import IntakeItem


@dataclass(frozen=True)
class IntakePlacementSuggestion:
    destination_key: str
    destination_label: str
    destination_href: str
    confidence: float
    reason: str
    signal_source: str


DESTINATION_CATALOG: dict[str, tuple[str, str]] = {
    "tickets": ("Tickets workspace", "/tickets"),
    "estimator": ("Estimator workspace", "/estimator"),
    "vendor": ("Vendor portal", "/vendor"),
    "safety": ("Safety module", "/modules/safety_manager/incidents"),
    "extraction_queue": ("Extraction queue review", "/extraction-queue"),
}


def _parse_entities(raw: str) -> dict[str, str]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return {str(key): str(value or "") for key, value in parsed.items()}


def _build_suggestion(
    destination_key: str,
    *,
    confidence: float,
    reason: str,
    signal_source: str,
) -> IntakePlacementSuggestion:
    label, href = DESTINATION_CATALOG[destination_key]
    return IntakePlacementSuggestion(
        destination_key=destination_key,
        destination_label=label,
        destination_href=href,
        confidence=max(0.0, min(confidence, 1.0)),
        reason=reason,
        signal_source=signal_source,
    )


def suggest_intake_placement(item: IntakeItem) -> IntakePlacementSuggestion:
    entities = _parse_entities(item.extracted_entities)
    summary = (item.extracted_summary or "").lower()
    extracted_text = (item.extracted_text or "").lower()
    document_type = (item.document_type or "general").lower()

    if document_type == "ticket" or entities.get("ticket_number", "").strip():
        return _build_suggestion(
            "tickets",
            confidence=0.92,
            reason="Ticket signals were detected in OCR/extracted fields.",
            signal_source="document_type+entities",
        )

    if any(token in summary for token in ("estimate", "bid", "proposal")) or any(
        token in extracted_text for token in ("scope of work", "estimate", "proposal")
    ):
        return _build_suggestion(
            "estimator",
            confidence=0.86,
            reason="Estimating language was detected in extracted content.",
            signal_source="summary+text",
        )

    if any(token in summary for token in ("invoice", "purchase order", "delivery", "compliance")) or any(
        token in extracted_text for token in ("invoice", "po #", "purchase order", "certificate of insurance")
    ):
        return _build_suggestion(
            "vendor",
            confidence=0.83,
            reason="Vendor/procurement indicators were detected in extraction results.",
            signal_source="summary+text",
        )

    if any(token in summary for token in ("safety", "incident", "osha")) or any(
        token in extracted_text for token in ("near miss", "incident", "osha", "safety")
    ):
        return _build_suggestion(
            "safety",
            confidence=0.79,
            reason="Safety-related indicators were detected in OCR text.",
            signal_source="summary+text",
        )

    return _build_suggestion(
        "extraction_queue",
        confidence=0.55,
        reason="No strong routing signal was detected; manual review is recommended.",
        signal_source="fallback",
    )
