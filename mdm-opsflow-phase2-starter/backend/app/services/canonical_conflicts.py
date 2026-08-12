from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from app.models import IntakeItem
from app.services.canonical_intake import build_canonical_document


_QUANTITY_CY_PATTERN = re.compile(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:cy|c\.y\.|cubic\s*yards?)\b", re.IGNORECASE)

# Lower rank value means higher authority.
_DOCUMENT_PRECEDENCE: dict[str, int] = {
    "contract": 1,
    "change_order": 1,
    "addendum": 2,
    "plan_document": 3,
    "specification": 3,
    "bid_schedule": 4,
    "vendor_quote": 5,
    "subcontractor_quote": 5,
    "quantity_takeoff": 6,
    "estimate": 7,
    "general": 8,
}


@dataclass(frozen=True)
class CanonicalValueProvenance:
    item_id: str
    field_name: str
    value: float
    unit: str
    document_type: str
    document_subtype: str
    source_text: str
    page: int | None
    confidence: float
    created_at: datetime


@dataclass(frozen=True)
class ConflictSuggestion:
    field_name: str
    candidates: tuple[CanonicalValueProvenance, ...]
    recommended: CanonicalValueProvenance
    reason: str


def _precedence_rank(document_type: str) -> int:
    return _DOCUMENT_PRECEDENCE.get((document_type or "general").lower(), 8)


def _parse_cy_values(text: str) -> list[float]:
    values: list[float] = []
    for match in _QUANTITY_CY_PATTERN.finditer(text or ""):
        raw_value = match.group(1).replace(",", "")
        try:
            values.append(float(raw_value))
        except ValueError:
            continue
    return values


def _extract_export_quantity(item: IntakeItem) -> CanonicalValueProvenance | None:
    canonical = build_canonical_document(item)
    text = canonical.extracted_text or canonical.summary
    if "export" not in text and "excavation" not in text:
        return None

    values = _parse_cy_values(text)
    if not values:
        return None

    # Prefer the last quantity in text because addenda often state revised values last.
    selected_value = values[-1]
    line_text = ""
    for line in (canonical.extracted_text or "").splitlines():
        if "cy" in line.lower() and ("export" in line.lower() or "excavation" in line.lower()):
            line_text = line.strip()
    if not line_text:
        line_text = "export quantity candidate detected"

    return CanonicalValueProvenance(
        item_id=item.id,
        field_name="export_quantity",
        value=selected_value,
        unit="CY",
        document_type=canonical.document_type,
        document_subtype=canonical.document_subtype,
        source_text=line_text,
        page=1,
        confidence=canonical.confidence,
        created_at=item.created_at,
    )


def build_quantity_conflict_suggestions(items: list[IntakeItem]) -> list[ConflictSuggestion]:
    candidates: list[CanonicalValueProvenance] = []
    for item in items:
        extracted = _extract_export_quantity(item)
        if extracted is not None:
            candidates.append(extracted)

    if len(candidates) < 2:
        return []

    unique_values = {round(candidate.value, 6) for candidate in candidates}
    if len(unique_values) < 2:
        return []

    sorted_candidates = sorted(
        candidates,
        key=lambda candidate: (
            _precedence_rank(candidate.document_type),
            -candidate.created_at.timestamp(),
        ),
    )
    recommended = sorted_candidates[0]
    reason = (
        f"Recommended from highest precedence source ({recommended.document_type}) "
        f"with latest timestamp tie-breaker."
    )

    return [
        ConflictSuggestion(
            field_name="export_quantity",
            candidates=tuple(candidates),
            recommended=recommended,
            reason=reason,
        )
    ]
