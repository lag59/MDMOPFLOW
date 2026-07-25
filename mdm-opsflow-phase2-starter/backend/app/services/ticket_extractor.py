from __future__ import annotations

import re


TICKET_NUMBER_PATTERN = re.compile(r"(?:ticket|ticket\s*#|ticket\s*number)\s*[:#-]?\s*([A-Za-z0-9-]{3,})", re.IGNORECASE)
DRIVER_PATTERN = re.compile(r"driver\s*[:#-]\s*([A-Za-z][A-Za-z\s'.-]{1,80})", re.IGNORECASE)
TRUCK_PATTERN = re.compile(r"truck\s*[:#-]\s*([A-Za-z0-9\s-]{1,40})", re.IGNORECASE)
MATERIAL_PATTERN = re.compile(r"material\s*[:#-]\s*([A-Za-z][A-Za-z\s-]{1,80})", re.IGNORECASE)


def _first_group(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    return match.group(1).strip()


def extract_ticket_preview(raw_text: str) -> tuple[dict[str, str], str, float]:
    """Return light-weight ticket signals from extracted text.

    This is intentionally deterministic and cheap so we can run it during upload.
    """
    text = raw_text.strip()
    if not text:
        return {}, "", 0.0

    fields = {
        "ticket_number": _first_group(TICKET_NUMBER_PATTERN, text),
        "driver": _first_group(DRIVER_PATTERN, text),
        "truck": _first_group(TRUCK_PATTERN, text),
        "material": _first_group(MATERIAL_PATTERN, text),
    }
    entities = {key: value for key, value in fields.items() if value}

    if not entities:
        return {}, "No ticket metadata detected during first-pass extraction.", 0.25

    confidence = 0.25 + (0.18 * len(entities))
    confidence = min(confidence, 0.95)

    summary_parts: list[str] = []
    if entities.get("ticket_number"):
        summary_parts.append(f"Ticket {entities['ticket_number']}")
    if entities.get("driver"):
        summary_parts.append(f"Driver {entities['driver']}")
    if entities.get("truck"):
        summary_parts.append(f"Truck {entities['truck']}")
    if entities.get("material"):
        summary_parts.append(f"Material {entities['material']}")

    summary = "; ".join(summary_parts)
    return entities, summary, confidence
