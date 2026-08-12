from __future__ import annotations

import re
from typing import Any

from app.services.canonical_intake import CanonicalDocument


def _extract_first(patterns: tuple[str, ...], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_decimal(pattern: str, text: str) -> tuple[str, str]:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return "", ""
    return match.group(1).replace(",", "").strip(), (match.group(2) or "").strip()


def _extract_decimal_candidates(
    pattern: str,
    text: str,
    *,
    value_group: int,
    unit_group: int,
    context_group: int | None = None,
) -> list[tuple[str, str, str]]:
    candidates: list[tuple[str, str, str]] = []
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        value = (match.group(value_group) or "").replace(",", "").strip()
        unit = (match.group(unit_group) or "").strip()
        context = (match.group(context_group) or "") if context_group is not None else ""
        source_text = f"{context}{value} {unit}".strip()
        if value:
            candidates.append((value, unit, source_text))
    return candidates


def _entry(
    *,
    value: str,
    unit: str,
    source_document_id: str,
    source_document_type: str,
    original_source_text: str,
    confidence: float,
    effective_date: str = "",
    authority_level: str = "informational",
    page: int | None = 1,
) -> dict[str, Any]:
    return {
        "value": value,
        "unit": unit,
        "source_document_id": source_document_id,
        "source_document_type": source_document_type,
        "page": page,
        "original_source_text": original_source_text,
        "confidence": max(0.0, min(confidence, 1.0)),
        "effective_date": effective_date,
        "authority_level": authority_level,
    }


def build_bid_package_payload(
    *,
    source_document_id: str,
    canonical_doc: CanonicalDocument,
) -> dict[str, list[dict[str, Any]]]:
    text = f"{canonical_doc.summary}\n{canonical_doc.extracted_text}"

    payload: dict[str, list[dict[str, Any]]] = {
        "project_identity": [],
        "bid_information": [],
        "scope": [],
        "quantities": [],
        "materials": [],
        "labor": [],
        "equipment": [],
        "vendor_quotes": [],
        "subcontractor_quotes": [],
        "haul_costs": [],
        "geotechnical_conditions": [],
        "allowances": [],
        "exclusions": [],
        "alternates": [],
        "addenda": [],
        "internal_costs": [],
        "risk_items": [],
    }

    project_name = canonical_doc.project.get("project_name", "")
    project_number = canonical_doc.project.get("project_number", "")
    vendor_name = canonical_doc.vendor.get("name", "")
    reference_number = canonical_doc.document_reference_number
    document_date = canonical_doc.dates.get("quote_date", "") or canonical_doc.dates.get("invoice_date", "")

    if project_name:
        payload["project_identity"].append(
            _entry(
                value=project_name,
                unit="",
                source_document_id=source_document_id,
                source_document_type=canonical_doc.document_type,
                original_source_text=project_name,
                confidence=canonical_doc.confidence,
                effective_date=document_date,
                authority_level="document",
            )
        )

    if project_number:
        payload["project_identity"].append(
            _entry(
                value=project_number,
                unit="",
                source_document_id=source_document_id,
                source_document_type=canonical_doc.document_type,
                original_source_text=project_number,
                confidence=canonical_doc.confidence,
                effective_date=document_date,
                authority_level="document",
            )
        )

    if reference_number:
        payload["bid_information"].append(
            _entry(
                value=reference_number,
                unit="",
                source_document_id=source_document_id,
                source_document_type=canonical_doc.document_type,
                original_source_text=reference_number,
                confidence=canonical_doc.confidence,
                effective_date=document_date,
                authority_level="document",
            )
        )

    if vendor_name:
        payload["vendor_quotes"].append(
            _entry(
                value=vendor_name,
                unit="",
                source_document_id=source_document_id,
                source_document_type=canonical_doc.document_type,
                original_source_text=vendor_name,
                confidence=canonical_doc.confidence,
                effective_date=document_date,
                authority_level="vendor",
            )
        )

    distance_candidates = _extract_decimal_candidates(
        r"([^\n]{0,120}?)(\d+(?:\.\d+)?)\s*(miles?|mi)\b",
        text,
        value_group=2,
        unit_group=3,
        context_group=1,
    )
    if distance_candidates:
        seen_distance: set[tuple[str, str]] = set()
        for value, unit, source_text in distance_candidates:
            key = (value, unit.lower())
            if key in seen_distance:
                continue
            seen_distance.add(key)
            authority_level = "addendum" if "addendum" in source_text.lower() or "revised" in source_text.lower() else "quote"
            payload["haul_costs"].append(
                _entry(
                    value=value,
                    unit=unit or "miles",
                    source_document_id=source_document_id,
                    source_document_type=canonical_doc.document_type,
                    original_source_text=source_text,
                    confidence=0.8,
                    effective_date=document_date,
                    authority_level=authority_level,
                )
            )

    quantity_candidates = _extract_decimal_candidates(
        r"([^\n]{0,120}?)(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(cy|cubic\s*yards?|lf|tons?)\b",
        text,
        value_group=2,
        unit_group=3,
        context_group=1,
    )
    if quantity_candidates:
        seen_quantity: set[tuple[str, str]] = set()
        for value, unit, source_text in quantity_candidates:
            key = (value, unit.lower())
            if key in seen_quantity:
                continue
            seen_quantity.add(key)
            authority_level = "addendum" if "addendum" in source_text.lower() or "revised" in source_text.lower() else "document"
            payload["quantities"].append(
                _entry(
                    value=value,
                    unit=unit,
                    source_document_id=source_document_id,
                    source_document_type=canonical_doc.document_type,
                    original_source_text=source_text,
                    confidence=0.75,
                    effective_date=document_date,
                    authority_level=authority_level,
                )
            )

    shrink_value, _ = _extract_decimal(r"shrink\s*factor\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(%)?", text)
    if shrink_value:
        payload["geotechnical_conditions"].append(
            _entry(
                value=shrink_value,
                unit="%",
                source_document_id=source_document_id,
                source_document_type=canonical_doc.document_type,
                original_source_text=f"shrink factor {shrink_value}%",
                confidence=0.82,
                effective_date=document_date,
                authority_level="geotech",
            )
        )

    swell_value, _ = _extract_decimal(r"swell\s*factor\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(%)?", text)
    if swell_value:
        payload["geotechnical_conditions"].append(
            _entry(
                value=swell_value,
                unit="%",
                source_document_id=source_document_id,
                source_document_type=canonical_doc.document_type,
                original_source_text=f"swell factor {swell_value}%",
                confidence=0.82,
                effective_date=document_date,
                authority_level="geotech",
            )
        )

    allowance_candidates = _extract_decimal_candidates(
        r"([^\n]{0,120}?undercut\s*(?:allowance)?\s*[:=]?\s*)(\d+(?:\.\d+)?)\s*(cy|cubic\s*yards?)",
        text,
        value_group=2,
        unit_group=3,
        context_group=1,
    )
    if allowance_candidates:
        seen_allowance: set[tuple[str, str]] = set()
        for value, unit, source_text in allowance_candidates:
            key = (value, unit.lower())
            if key in seen_allowance:
                continue
            seen_allowance.add(key)
            authority_level = "addendum" if "addendum" in source_text.lower() or "revised" in source_text.lower() else "geotech"
            payload["allowances"].append(
                _entry(
                    value=value,
                    unit=unit,
                    source_document_id=source_document_id,
                    source_document_type=canonical_doc.document_type,
                    original_source_text=source_text,
                    confidence=0.78,
                    effective_date=document_date,
                    authority_level=authority_level,
                )
            )

    if canonical_doc.document_type == "addendum":
        revised_qty = _extract_first((r"revised\s+to\s+(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:cy|cubic\s*yards?)",), text)
        if revised_qty:
            payload["addenda"].append(
                _entry(
                    value=revised_qty.replace(",", ""),
                    unit="CY",
                    source_document_id=source_document_id,
                    source_document_type=canonical_doc.document_type,
                    original_source_text=f"revised to {revised_qty} CY",
                    confidence=0.9,
                    effective_date=document_date,
                    authority_level="addendum",
                )
            )

    if canonical_doc.document_type in {"internal_cost_worksheet", "equipment_rental_quote"}:
        rate = _extract_first((r"(?:weekly\s*rate|unit\s*price|rate)\s*[:#-]?\s*\$?([\d,]+(?:\.\d+)?)",), text)
        if rate:
            payload["internal_costs"].append(
                _entry(
                    value=rate.replace(",", ""),
                    unit="USD",
                    source_document_id=source_document_id,
                    source_document_type=canonical_doc.document_type,
                    original_source_text=f"rate {rate}",
                    confidence=0.76,
                    effective_date=document_date,
                    authority_level="estimate",
                )
            )

    risk_phrase = _extract_first(
        (
            r"(export\s+amount\s+still\s+needs\s+reconciliation)",
            r"(assumption[s]?\s*[:].{1,120})",
        ),
        text,
    )
    if risk_phrase:
        payload["risk_items"].append(
            _entry(
                value=risk_phrase,
                unit="",
                source_document_id=source_document_id,
                source_document_type=canonical_doc.document_type,
                original_source_text=risk_phrase,
                confidence=0.7,
                effective_date=document_date,
                authority_level="review",
            )
        )

    return payload
