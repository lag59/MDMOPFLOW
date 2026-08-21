from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


AUTO_ROUTE_MIN_CONFIDENCE = 0.72
AUTO_POST_FINANCIAL_OR_TICKET_MIN_CONFIDENCE = 0.90

DOCUMENT_RULES: dict[str, tuple[tuple[str, ...], str, int]] = {
    "invitation_to_bid": (("invitation to bid", "instructions to bidders", "bid due", "project no"), "Estimator > Bid Packages > Invitation to Bid", 80),
    "scope_of_work": (("scope of work", "earthwork", "storm drainage", "water / sewer", "exclusions"), "Estimator > Project Documents > Scope", 78),
    "bid_schedule": (("bid schedule", "unit price", "extension", "base bid total"), "Estimator > Bid Schedule", 90),
    "material_quote": (("material quotation", "material quote", "quote no", "unit price", "valid through", "freight"), "Estimator > Vendors > Material Quotes", 82),
    "hauling_disposal_quote": (("hauling & disposal quote", "hauling / disposal quote", "truck type", "truck-hour", "disposal fee", "one-way distance"), "Estimator > Hauling > Vendor Quotes", 88),
    "geotechnical_summary": (("geotechnical summary", "geotechnical", "subsurface conditions", "groundwater", "shrink factor", "swell factor"), "Estimator > Project Documents > Geotechnical", 76),
    "addendum": (("addendum no", "addendum", "reference change", "revised from", "bid due date unchanged"), "Estimator > Addenda & Revisions", 100),
    "equipment_rental_quote": (("equipment rental quote", "rental period", "weekly rate", "4-week extension"), "Estimator > Equipment > Rental Quotes", 84),
    "subcontractor_proposal": (("subcontractor proposal", "lump sum", "included", "excluded"), "Estimator > Subcontractors > Proposals", 84),
    "quantity_takeoff": (("quantity takeoff worksheet", "quantity takeoff", "plan qty", "estimator qty", "variance"), "Estimator > Quantity Takeoff", 92),
    "internal_cost_worksheet": (("internal cost worksheet", "cost code", "labor", "equipment", "material/sub", "subtotal direct cost"), "Estimator > Internal Cost", 94),
    "haul_ticket": (("haul ticket", "ticket no", "truck", "driver", "material", "time in", "time out"), "Tickets > Hauling", 98),
}

UNKNOWN_ROUTE = "Review Queue > Unclassified"

PROJECT_ALIASES = {
    "n. ridge commerce pk ph 2": "North Ridge Commerce Park - Phase 2",
    "nrcp ph2": "North Ridge Commerce Park - Phase 2",
    "north ridge commerce park - phase 2": "North Ridge Commerce Park - Phase 2",
}
UNIT_ALIASES = {
    "cy": "CY",
    "c.y.": "CY",
    "cubic yards": "CY",
    "lf": "LF",
    "linear feet": "LF",
    "ton": "TON",
    "tons": "TON",
    "ea": "EA",
    "each": "EA",
    "ls": "LS",
    "ac": "AC",
    "acres": "AC",
}
VENDOR_ALIASES = {
    "triangle site supply": "Triangle Site Supply, LLC",
    "carolina haul services": "Carolina Haul Services",
    "piedmont heavy rental": "Piedmont Heavy Rental",
    "greenline erosion services": "GreenLine Erosion Services",
}


@dataclass(frozen=True)
class IntakeClassification:
    document_type: str
    confidence: float
    recommended_route: str
    matched_keywords: tuple[str, ...]
    requires_human_review: bool
    reason_for_review: str | None


@dataclass(frozen=True)
class IntakeRoutingResult:
    document_type: str
    classification_confidence: float
    recommended_route: str
    project: dict[str, Any]
    vendor: dict[str, Any]
    extracted_fields: dict[str, Any]
    uncertain_fields: list[str]
    conflicts: list[dict[str, Any]]
    requires_human_review: bool
    reason_for_review: str | None
    normalized_text: str

    def flattened_entities(self) -> dict[str, str]:
        entities: dict[str, str] = {
            "document_type": self.document_type,
            "recommended_route": self.recommended_route,
        }
        if self.project.get("name"):
            entities["project_name"] = str(self.project["name"])
        if self.project.get("number"):
            entities["project_number"] = str(self.project["number"])
        if self.vendor.get("name"):
            entities["vendor_name"] = str(self.vendor["name"])
        if self.vendor.get("document_number"):
            entities["reference_number"] = str(self.vendor["document_number"])

        for key, value in self.extracted_fields.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                entities[key] = str(value)
        return entities


def normalize_ocr_text(text: str) -> str:
    normalized = text.replace("\u00a0", " ").replace("–", "-").replace("—", "-")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"(?i)(distance)(\d)", r"\1 \2", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def parse_number(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(re.sub(r"[,$%]", "", value))
    except ValueError:
        return None


def first_match(patterns: tuple[str, ...], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def normalize_project_name(value: str | None) -> str | None:
    if not value:
        return None
    key = re.sub(r"\s+", " ", value.strip().lower())
    return PROJECT_ALIASES.get(key, value.strip())


def classify_document(text: str) -> IntakeClassification:
    lowered = text.lower()
    scored: list[tuple[float, str, tuple[str, ...], str, int]] = []
    for document_type, (keywords, route, priority) in DOCUMENT_RULES.items():
        matches = tuple(keyword for keyword in keywords if keyword in lowered)
        if matches:
            scored.append((len(matches) * 20 + priority * 0.15, document_type, matches, route, priority))

    if not scored:
        return IntakeClassification("unknown", 0.0, UNKNOWN_ROUTE, (), True, "No supported document type matched OCR text.")

    scored.sort(reverse=True)
    _, document_type, matches, route, priority = scored[0]
    confidence = min(0.99, 0.40 + len(matches) * 0.12 + priority / 500)
    confidence = round(confidence, 3)
    requires_review = confidence < AUTO_ROUTE_MIN_CONFIDENCE
    return IntakeClassification(
        document_type=document_type,
        confidence=confidence,
        recommended_route=route,
        matched_keywords=matches,
        requires_human_review=requires_review,
        reason_for_review="Classification confidence below auto-route threshold." if requires_review else None,
    )


def extract_project_name(text: str) -> str | None:
    value = first_match((r"^Project\s+(.+)$", r"^Project\s*[:#-]\s*(.+)$", r"^(North Ridge Commerce Park\s*-\s*Phase 2).*$"), text)
    if value:
        value = value.split("|")[0].strip()
    return normalize_project_name(value)


def extract_project_number(text: str) -> str | None:
    return first_match((r"Project\s*(?:No\.?|Number)\s*[:#-]?\s*([A-Z0-9-]+)", r"\b(NRCP-\d{2}-\d{3})\b", r"\b(NRCP-PH2)\b"), text)


def extract_vendor(text: str) -> str | None:
    lowered = text.lower()
    for key, value in VENDOR_ALIASES.items():
        if key in lowered:
            return value
    return None


def extract_document_number(text: str) -> str | None:
    return first_match(
        (
            r"Ticket\s*No\.?\s*[:#-]?\s*([A-Z0-9-]+)",
            r"Quote\s*No\.?\s*[:#-]?\s*([A-Z0-9-]+)",
            r"Quote\s*Number\s*[:#-]?\s*([A-Z0-9-]+)",
            r"Proposal\s*No\.?\s*[:#-]?\s*([A-Z0-9-]+)",
        ),
        text,
    )


def extract_haul_ticket(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "ticket_number": first_match((r"Ticket\s*No\.?\s*[:#-]?\s*([A-Z0-9-]+)",), text),
        "date": first_match((r"^Date\s+([0-9/.-]+)$", r"^Date\s*[:#-]\s*([0-9/.-]+)$"), text),
        "project": normalize_project_name(first_match((r"^Project\s+(.+)$", r"^Project\s*[:#-]\s*(.+)$"), text)),
        "truck": first_match((r"^Truck\s+([A-Z0-9-]+)$", r"^Truck\s*[:#-]\s*([A-Z0-9-]+)$"), text),
        "driver": first_match((r"^Driver\s+(.+)$", r"^Driver\s*[:#-]\s*(.+)$"), text),
        "material": first_match((r"^Material\s+(.+)$", r"^Material\s*[:#-]\s*(.+)$"), text),
        "origin": first_match((r"^Origin\s+(.+)$",), text),
        "destination": first_match((r"^Destination\s+(.+)$",), text),
        "time_in": first_match((r"^Time\s*In\s+([0-9:apm ]+)$",), text),
        "time_out": first_match((r"^Time\s*Out\s+([0-9:apm ]+)$",), text),
    }
    match = re.search(r"^Load\s+([\d,.]+)\s*([A-Za-z.]+)", text, re.IGNORECASE | re.MULTILINE)
    if match:
        fields["load_value"] = parse_number(match.group(1))
        fields["load_unit"] = UNIT_ALIASES.get(match.group(2).lower(), match.group(2).upper())
    return fields


def extract_hauling_quote(text: str) -> dict[str, Any]:
    return {
        "material": first_match((r"^Material\s+(.+)$", r"^Material\s*[:#-]\s*(.+)$"), text),
        "assumed_quantity_cy": parse_number(first_match((r"Assumed Quantity\s*([\d,]+)\s*CY",), text)),
        "one_way_distance_miles": parse_number(first_match((r"(?:One-Way|Assumed One-Way) Distance\s*[:#-]?\s*([\d.]+)\s*miles",), text)),
        "truck_type": first_match((r"^Truck Type\s+(.+)$", r"^Truck Type\s*[:#-]\s*(.+)$"), text),
        "hourly_rate": parse_number(first_match((r"Rate\s*\$([\d,.]+)\s*per truck-hour",), text)),
        "disposal_fee_per_cy": parse_number(first_match((r"Disposal Fee\s*\$([\d,.]+)\s*per\s*CY",), text)),
    }


def extract_bid_schedule(text: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    pattern = re.compile(r"^\s*(\d+)\s+(.+?)\s+([\d,]+)\s+(LS|AC|CY|LF|EA|TON)\s+\$([\d,.]+)\s+\$([\d,.]+)\s*$", re.IGNORECASE | re.MULTILINE)
    for match in pattern.finditer(text):
        items.append(
            {
                "item": int(match.group(1)),
                "description": match.group(2).strip(),
                "quantity": parse_number(match.group(3)),
                "unit": match.group(4).upper(),
                "unit_price": parse_number(match.group(5)),
                "extension": parse_number(match.group(6)),
            }
        )
    return {"items": items, "base_bid_total": parse_number(first_match((r"Base Bid Total.*?\$([\d,.]+)",), text))}


def extract_quantity_takeoff(text: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    pattern = re.compile(r"^(Earthwork|Storm|Water|Sewer)\s+(.+?)\s+([\d,]+)\s+(CY|LF|EA|TON)\s+([\d,]+)\s+(CY|LF|EA|TON)\s+([+-]?[\d,]+|0)(?:\s+(CY|LF|EA|TON))?\s*$", re.IGNORECASE | re.MULTILINE)
    for match in pattern.finditer(text):
        items.append(
            {
                "category": match.group(1),
                "description": match.group(2).strip(),
                "plan_qty": parse_number(match.group(3)),
                "plan_unit": match.group(4).upper(),
                "estimator_qty": parse_number(match.group(5)),
                "estimator_unit": match.group(6).upper(),
                "variance": parse_number(match.group(7)),
            }
        )
    return {"items": items}


def extract_addendum(text: str) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    export_match = re.search(r"Export quantity revised from\s*([\d,]+)\s*CY\s*to\s*([\d,]+)\s*CY", text, re.IGNORECASE)
    if export_match:
        changes.append({"field": "export_quantity_cy", "from": parse_number(export_match.group(1)), "to": parse_number(export_match.group(2)), "precedence": "authoritative_revision"})
    pipe_match = re.search(r"revised from\s*(24-in RCP)\s*to\s*(30-in RCP)\s*for\s*([\d,]+)\s*LF", text, re.IGNORECASE)
    if pipe_match:
        changes.append({"field": "storm_pipe_revision", "from": pipe_match.group(1), "to": pipe_match.group(2), "quantity": parse_number(pipe_match.group(3)), "unit": "LF", "precedence": "authoritative_revision"})
    rock_match = re.search(r"Rock allowance increased from\s*([\d,]+)\s*CY\s*to\s*([\d,]+)\s*CY", text, re.IGNORECASE)
    if rock_match:
        changes.append({"field": "rock_allowance_cy", "from": parse_number(rock_match.group(1)), "to": parse_number(rock_match.group(2)), "precedence": "authoritative_revision"})
    return {"changes": changes}


def extract_internal_cost(text: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    pattern = re.compile(r"^(\d{2}-\d{3})\s+(.+?)\s+\$([\d,.]+)\s+\$([\d,.]+)\s+\$([\d,.]+)\s+\$([\d,.]+)\s*$", re.MULTILINE)
    for match in pattern.finditer(text):
        rows.append({"cost_code": match.group(1), "description": match.group(2), "labor": parse_number(match.group(3)), "equipment": parse_number(match.group(4)), "material_sub": parse_number(match.group(5)), "total": parse_number(match.group(6))})
    return {
        "cost_lines": rows,
        "subtotal_direct_cost": parse_number(first_match((r"Subtotal direct cost:\s*\$([\d,.]+)",), text)),
        "overhead_pct": parse_number(first_match((r"Overhead:\s*([\d.]+)%",), text)),
        "profit_pct": parse_number(first_match((r"Profit:\s*([\d.]+)%",), text)),
        "bond_pct": parse_number(first_match((r"Bond:\s*([\d.]+)%",), text)),
    }


def extract_generic_quote(text: str) -> dict[str, Any]:
    return {
        "quote_number": extract_document_number(text),
        "project": extract_project_name(text),
        "vendor": extract_vendor(text),
        "lump_sum": parse_number(first_match((r"Lump Sum\s*\$([\d,.]+)",), text)),
    }


EXTRACTORS = {
    "haul_ticket": extract_haul_ticket,
    "hauling_disposal_quote": extract_hauling_quote,
    "bid_schedule": extract_bid_schedule,
    "quantity_takeoff": extract_quantity_takeoff,
    "addendum": extract_addendum,
    "internal_cost_worksheet": extract_internal_cost,
    "material_quote": extract_generic_quote,
    "equipment_rental_quote": extract_generic_quote,
    "subcontractor_proposal": extract_generic_quote,
}


def extract_noop(_: str) -> dict[str, Any]:
    return {}


def route_ocr_document(raw_text: str) -> IntakeRoutingResult:
    normalized_text = normalize_ocr_text(raw_text)
    classification = classify_document(normalized_text)
    extracted_fields = EXTRACTORS.get(classification.document_type, extract_noop)(normalized_text)
    project_name = extract_project_name(normalized_text) or extracted_fields.get("project")
    project_number = extract_project_number(normalized_text)
    vendor_name = extract_vendor(normalized_text) or extracted_fields.get("vendor")
    document_number = extract_document_number(normalized_text) or extracted_fields.get("quote_number") or extracted_fields.get("ticket_number")

    uncertain_fields: list[str] = []
    if classification.document_type == "haul_ticket":
        required = ("ticket_number", "date", "truck", "material", "load_value", "load_unit")
        uncertain_fields.extend(field for field in required if not extracted_fields.get(field))
    if classification.confidence < AUTO_ROUTE_MIN_CONFIDENCE:
        uncertain_fields.append("document_type")
    if not project_name and classification.document_type != "unknown":
        uncertain_fields.append("project.name")

    requires_review = classification.requires_human_review or bool(uncertain_fields)
    reason_for_review = classification.reason_for_review
    if requires_review and not reason_for_review:
        reason_for_review = "Required fields or project match need reviewer confirmation."

    return IntakeRoutingResult(
        document_type=classification.document_type,
        classification_confidence=classification.confidence,
        recommended_route=classification.recommended_route,
        project={"name": project_name, "number": project_number, "match_confidence": 0.0},
        vendor={"name": vendor_name, "document_number": document_number},
        extracted_fields={key: value for key, value in extracted_fields.items() if value not in (None, "", [])},
        uncertain_fields=uncertain_fields,
        conflicts=[],
        requires_human_review=requires_review,
        reason_for_review=reason_for_review,
        normalized_text=normalized_text,
    )


def should_use_ai_fallback(result: IntakeRoutingResult) -> bool:
    return result.classification_confidence < AUTO_ROUTE_MIN_CONFIDENCE or result.document_type == "unknown" or bool(result.uncertain_fields)