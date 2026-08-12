from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.models import IntakeItem


ESTIMATOR_DOCUMENT_TYPES = {
    "estimate",
    "estimator",
    "bid",
    "bid_schedule",
    "proposal",
    "takeoff",
    "quantity_takeoff",
    "addendum",
    "equipment_quote",
    "subcontractor_quote",
    "vendor_quote",
}

ACCOUNTING_DOCUMENT_TYPES = {
    "invoice",
    "ap_invoice",
    "billing_statement",
}

TICKET_DOCUMENT_TYPES = {
    "ticket",
    "haul_ticket",
}

ESTIMATOR_KEYWORDS = (
    "estimate",
    "bid",
    "bid schedule",
    "proposal",
    "takeoff",
    "scope of work",
    "quantity takeoff",
    "addendum",
    "subcontractor quote",
    "equipment quote",
    "vendor quote",
)

ACCOUNTING_KEYWORDS = (
    "invoice",
    "amount due",
    "bill to",
    "accounts payable",
    "payment terms",
)

TICKET_KEYWORDS = (
    "haul ticket",
    "ticket #",
    "truck",
    "driver",
    "material",
    "net weight",
)


@dataclass(frozen=True)
class CanonicalLineItem:
    description: str = ""
    quantity: float | None = None
    unit: str = ""
    unit_price: float | None = None


@dataclass(frozen=True)
class CanonicalSourceReference:
    field: str
    page: int | None
    source_text: str


@dataclass(frozen=True)
class CanonicalDocument:
    document_type: str
    document_subtype: str
    confidence: float
    project: dict[str, str] = field(default_factory=dict)
    vendor: dict[str, str] = field(default_factory=dict)
    dates: dict[str, str] = field(default_factory=dict)
    line_items: tuple[CanonicalLineItem, ...] = ()
    operational_data: dict[str, str] = field(default_factory=dict)
    source_references: tuple[CanonicalSourceReference, ...] = ()
    summary: str = ""
    extracted_text: str = ""
    entities: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RoutingScores:
    estimator_document_score: float
    accounting_document_score: float
    operational_ticket_score: float


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


def _as_float(value: str) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _guess_document_type(base_type: str, text_blob: str) -> tuple[str, str]:
    normalized = (base_type or "").strip().lower()

    if any(token in text_blob for token in ("vendor quote", "quote #", "quote number")):
        return "vendor_quote", "hauling_quote" if "haul" in text_blob else "general_quote"
    if "subcontractor quote" in text_blob:
        return "subcontractor_quote", "general"
    if "equipment quote" in text_blob:
        return "equipment_quote", "general"
    if any(token in text_blob for token in ("bid schedule", "bid item")):
        return "bid_schedule", "line_items"
    if any(token in text_blob for token in ("quantity takeoff", "takeoff")):
        return "quantity_takeoff", "quantities"
    if "addendum" in text_blob:
        return "addendum", "reconciliation"
    if any(token in text_blob for token in ("invoice", "accounts payable", "amount due")):
        return "invoice", "ap_invoice"
    if any(token in text_blob for token in ("haul ticket", "ticket #", "ticket number")):
        return "haul_ticket", "production"

    if normalized == "ticket":
        return "haul_ticket", "production"

    return normalized or "general", "general"


def build_canonical_document(item: IntakeItem) -> CanonicalDocument:
    entities = _parse_entities(item.extracted_entities)
    summary = (item.extracted_summary or "").strip()
    extracted_text = (item.extracted_text or "").strip()
    text_blob = f"{summary}\n{extracted_text}".lower()

    document_type, document_subtype = _guess_document_type(item.document_type or "", text_blob)

    project = {
        "project_name": entities.get("project_name", "").strip(),
        "project_number": entities.get("project_number", "").strip(),
    }
    vendor = {
        "name": entities.get("vendor_name", "").strip() or entities.get("contractor", "").strip(),
        "quote_number": entities.get("quote_number", "").strip(),
    }
    dates = {
        "quote_date": entities.get("quote_date", "").strip() or entities.get("date", "").strip(),
        "invoice_date": entities.get("invoice_date", "").strip(),
    }

    line_item = CanonicalLineItem(
        description=entities.get("line_item_description", "").strip() or entities.get("material", "").strip(),
        quantity=_as_float(entities.get("quantity", "")),
        unit=entities.get("unit", "").strip(),
        unit_price=_as_float(entities.get("unit_price", "")),
    )
    line_items = (line_item,) if line_item.description else ()

    operational_data = {
        "haul_distance_one_way_miles": entities.get("haul_distance_one_way_miles", "").strip(),
        "truck_type": entities.get("truck_type", "").strip() or entities.get("truck", "").strip(),
        "hourly_rate": entities.get("hourly_rate", "").strip(),
    }

    source_references: list[CanonicalSourceReference] = []
    if operational_data.get("haul_distance_one_way_miles"):
        source_references.append(
            CanonicalSourceReference(
                field="haul_distance_one_way_miles",
                page=1,
                source_text="Assumed One-Way Distance",
            )
        )

    return CanonicalDocument(
        document_type=document_type,
        document_subtype=document_subtype,
        confidence=float(item.classification_confidence or 0.0),
        project=project,
        vendor=vendor,
        dates=dates,
        line_items=line_items,
        operational_data=operational_data,
        source_references=tuple(source_references),
        summary=summary.lower(),
        extracted_text=extracted_text.lower(),
        entities=entities,
    )


def _cap(score: float) -> float:
    return max(0.0, min(score, 1.0))


def score_canonical_document(doc: CanonicalDocument) -> RoutingScores:
    estimator = 0.0
    accounting = 0.0
    tickets = 0.0

    if doc.document_type in ESTIMATOR_DOCUMENT_TYPES:
        estimator += 0.75
    estimator += min(0.2, 0.05 * sum(1 for token in ESTIMATOR_KEYWORDS if token in doc.summary))
    estimator += min(0.2, 0.05 * sum(1 for token in ESTIMATOR_KEYWORDS if token in doc.extracted_text))
    if doc.vendor.get("quote_number"):
        estimator += 0.05

    if doc.document_type in ACCOUNTING_DOCUMENT_TYPES:
        accounting += 0.8
    accounting += min(0.2, 0.05 * sum(1 for token in ACCOUNTING_KEYWORDS if token in doc.summary))
    accounting += min(0.2, 0.05 * sum(1 for token in ACCOUNTING_KEYWORDS if token in doc.extracted_text))

    ticket_number = (doc.entities.get("ticket_number") or "").strip()
    if doc.document_type in TICKET_DOCUMENT_TYPES:
        tickets += 0.7
    if ticket_number:
        tickets += 0.1
    if any((doc.entities.get(key) or "").strip() for key in ("driver", "truck", "material", "net_weight_lbs")):
        tickets += 0.1
    tickets += min(0.2, 0.04 * sum(1 for token in TICKET_KEYWORDS if token in doc.extracted_text))

    return RoutingScores(
        estimator_document_score=_cap(estimator),
        accounting_document_score=_cap(accounting),
        operational_ticket_score=_cap(tickets),
    )


def has_estimator_signals(*, document_type: str, summary: str, extracted_text: str, entities: dict[str, str]) -> bool:
    text_blob = f"{summary}\n{extracted_text}".lower()
    normalized_document_type, _ = _guess_document_type(document_type, text_blob)

    if normalized_document_type in ESTIMATOR_DOCUMENT_TYPES:
        return True

    if any(token in text_blob for token in ESTIMATOR_KEYWORDS):
        return True

    return bool((entities.get("quote_number") or "").strip())
