from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime

from app.models import IntakeItem


ESTIMATOR_DOCUMENT_TYPES = {
    "invitation_to_bid",
    "scope_of_work",
    "bid_schedule",
    "material_quote",
    "vendor_material_quote",
    "hauling_disposal_quote",
    "geotechnical_summary",
    "geotechnical_report",
    "addendum",
    "equipment_rental_quote",
    "subcontractor_proposal",
    "quantity_takeoff",
    "internal_cost_worksheet",
    "estimate",
}

ACCOUNTING_DOCUMENT_TYPES = {
    "invoice",
    "ap_invoice",
    "billing_statement",
}

TICKET_DOCUMENT_TYPES = {
    "haul_ticket",
    "haul_material_delivery_ticket",
}

ESTIMATOR_KEYWORDS = (
    "invitation to bid",
    "itb",
    "scope of work",
    "bid schedule",
    "vendor quote",
    "subcontractor proposal",
    "equipment rental",
    "quantity takeoff",
    "qto",
    "addendum",
    "geotechnical",
    "internal cost",
    "worksheet",
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
    "delivery ticket",
    "material ticket",
    "ticket #",
    "truck",
    "driver",
    "material",
    "net weight",
)

PROJECT_NUMBER_PATTERNS = (
    r"project\s*(?:#|number|no\.?)[\s:]*([a-z0-9\-_/]+)",
    r"job\s*(?:#|number|no\.?)[\s:]*([a-z0-9\-_/]+)",
)

REFERENCE_PATTERNS = (
    r"addendum\s*(?:#|no\.?)[\s:]*([a-z0-9\-_/]+)",
    r"quote\s*(?:#|number|no\.?)[\s:]*([a-z0-9\-_/]+)",
    r"proposal\s*(?:#|number|no\.?)[\s:]*([a-z0-9\-_/]+)",
    r"ticket\s*(?:#|number|no\.?)[\s:]*([a-z0-9\-_/]+)",
)

DATE_PATTERNS = (
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
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
    document_reference_number: str = ""
    line_items: tuple[CanonicalLineItem, ...] = ()
    operational_data: dict[str, str] = field(default_factory=dict)
    source_references: tuple[CanonicalSourceReference, ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    conflicting_evidence: tuple[str, ...] = ()
    summary: str = ""
    extracted_text: str = ""
    entities: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentIntelligence:
    primary_document_type: str
    subtype: str
    project_name: str
    project_number: str
    vendor_subcontractor: str
    document_date: str
    document_reference_number: str
    recommended_module: str
    confidence: float
    supporting_evidence: tuple[str, ...] = ()
    conflicting_evidence: tuple[str, ...] = ()


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

    if any(token in text_blob for token in ("invitation to bid", "itb")):
        return "invitation_to_bid", "solicitation"
    if "scope of work" in text_blob:
        return "scope_of_work", "scope"
    if any(token in text_blob for token in ("bid schedule", "bid item")):
        return "bid_schedule", "line_items"
    if any(token in text_blob for token in ("hauling quote", "disposal quote", "assumed one-way distance")):
        return "hauling_disposal_quote", "haul_pricing"
    if any(token in text_blob for token in ("vendor quote", "material quote")):
        return "vendor_material_quote", "pricing"
    if any(token in text_blob for token in ("geotechnical", "soil", "groundwater", "swell factor", "shrink factor")):
        return "geotechnical_report", "site_conditions"
    if any(token in text_blob for token in ("equipment rental", "weekly rate", "monthly rate")):
        return "equipment_rental_quote", "equipment_pricing"
    if any(token in text_blob for token in ("subcontractor proposal", "subcontract proposal")):
        return "subcontractor_proposal", "pricing"
    if any(token in text_blob for token in ("quantity takeoff", "takeoff")):
        return "quantity_takeoff", "quantities"
    if any(token in text_blob for token in ("internal cost worksheet", "cost worksheet", "crew cost", "burden")):
        return "internal_cost_worksheet", "internal_costs"
    if "addendum" in text_blob:
        return "addendum", "revision"
    if any(token in text_blob for token in ("invoice", "accounts payable", "amount due")):
        return "invoice", "ap_invoice"
    if any(token in text_blob for token in ("haul ticket", "delivery ticket", "material ticket")):
        return "haul_material_delivery_ticket", "transactional"

    if normalized == "material_quote":
        return "material_quote", "pricing"
    if normalized == "geotechnical_summary":
        return "geotechnical_summary", "site_conditions"
    if normalized == "haul_ticket":
        return "haul_ticket", "transactional"

    if normalized == "ticket":
        return "haul_material_delivery_ticket", "transactional"

    if normalized in {"quote", "proposal", "bid", "estimate"}:
        return "estimate", "general"

    return normalized or "general", "general"


def _extract_pattern(patterns: tuple[str, ...], text_blob: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text_blob, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_date(text_blob: str) -> str:
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text_blob)
        if match:
            candidate = match.group(0)
            try:
                if "-" in candidate and len(candidate) == 10:
                    datetime.strptime(candidate, "%Y-%m-%d")
                elif candidate.count("/") == 2:
                    month, day, year = candidate.split("/")
                    fmt = "%m/%d/%Y" if len(year) == 4 else "%m/%d/%y"
                    datetime.strptime(candidate, fmt)
                return candidate
            except ValueError:
                continue
    return ""


def build_canonical_document(item: IntakeItem) -> CanonicalDocument:
    entities = _parse_entities(item.extracted_entities)
    summary = (item.extracted_summary or "").strip()
    extracted_text = (item.extracted_text or "").strip()
    text_blob_raw = f"{summary}\n{extracted_text}"
    text_blob = text_blob_raw.lower()

    document_type, document_subtype = _guess_document_type(item.document_type or "", text_blob)

    project_number = entities.get("project_number", "").strip() or _extract_pattern(PROJECT_NUMBER_PATTERNS, text_blob_raw)
    project_name = entities.get("project_name", "").strip() or entities.get("job", "").strip()

    project = {
        "project_name": project_name,
        "project_number": project_number,
    }
    vendor = {
        "name": entities.get("vendor_name", "").strip() or entities.get("subcontractor_name", "").strip() or entities.get("contractor", "").strip(),
        "quote_number": entities.get("quote_number", "").strip(),
    }
    dates = {
        "quote_date": entities.get("quote_date", "").strip() or entities.get("date", "").strip() or _extract_date(text_blob_raw),
        "invoice_date": entities.get("invoice_date", "").strip(),
    }
    reference_number = (
        entities.get("reference_number", "").strip()
        or entities.get("quote_number", "").strip()
        or entities.get("ticket_number", "").strip()
        or _extract_pattern(REFERENCE_PATTERNS, text_blob_raw)
    )

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

    supporting_evidence: list[str] = []
    conflicting_evidence: list[str] = []

    if document_type in ESTIMATOR_DOCUMENT_TYPES:
        supporting_evidence.append(f"Document pattern matched estimator family: {document_type}")
    if reference_number:
        supporting_evidence.append(f"Reference detected: {reference_number}")
    if project_name:
        supporting_evidence.append(f"Project signal detected: {project_name}")
    if project_number:
        supporting_evidence.append(f"Project number detected: {project_number}")

    ticket_tokens_present = [token for token in TICKET_KEYWORDS if token in text_blob]
    if document_type in ESTIMATOR_DOCUMENT_TYPES and ticket_tokens_present:
        conflicting_evidence.append(
            "Ticket-like terms present but document context indicates estimating package content"
        )

    return CanonicalDocument(
        document_type=document_type,
        document_subtype=document_subtype,
        confidence=float(item.classification_confidence or 0.0),
        project=project,
        vendor=vendor,
        dates=dates,
        document_reference_number=reference_number,
        line_items=line_items,
        operational_data=operational_data,
        source_references=tuple(source_references),
        supporting_evidence=tuple(supporting_evidence),
        conflicting_evidence=tuple(conflicting_evidence),
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

    # Hard guard: estimator-family bid package docs should not be treated as
    # transactional tickets just because they mention hauling vocabulary.
    if doc.document_type in ESTIMATOR_DOCUMENT_TYPES:
        tickets = min(tickets, 0.45)

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


def build_document_intelligence(doc: CanonicalDocument, scores: RoutingScores, *, recommended_module: str) -> DocumentIntelligence:
    confidence = max(scores.estimator_document_score, scores.accounting_document_score, scores.operational_ticket_score, doc.confidence)
    return DocumentIntelligence(
        primary_document_type=doc.document_type,
        subtype=doc.document_subtype,
        project_name=doc.project.get("project_name", ""),
        project_number=doc.project.get("project_number", ""),
        vendor_subcontractor=doc.vendor.get("name", ""),
        document_date=doc.dates.get("quote_date", "") or doc.dates.get("invoice_date", ""),
        document_reference_number=doc.document_reference_number,
        recommended_module=recommended_module,
        confidence=float(max(0.0, min(confidence, 1.0))),
        supporting_evidence=doc.supporting_evidence,
        conflicting_evidence=doc.conflicting_evidence,
    )
