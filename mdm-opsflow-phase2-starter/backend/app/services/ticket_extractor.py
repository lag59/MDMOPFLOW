from __future__ import annotations

import re

from app.services.llm_client import summarize_ticket_preview


TICKET_NUMBER_PATTERN = re.compile(r"(?:ticket|ticket\s*#|ticket\s*number)\s*[:#-]?\s*([A-Za-z0-9-]{3,})", re.IGNORECASE)
INVOICE_NUMBER_PATTERN = re.compile(
    r"(?:\binvoice\b|\binv\b)\s*(?:#|number|no\.?|num\.)?\s*[:#-]?\s*([A-Za-z0-9-]{3,})",
    re.IGNORECASE,
)
DRIVER_PATTERN = re.compile(r"driver\s*[:#-]\s*([^\r\n]{1,120})", re.IGNORECASE)
# Allow # as separator; strip trailing noise like commas
TRUCK_PATTERN = re.compile(r"(?:truck|unit|truck\s*(?:no\.?|size)|unit\s*no\.)\s*[:#-]?\s*([^\r\n]{1,80})", re.IGNORECASE)
MATERIAL_PATTERN = re.compile(r"material\s*[:#-]\s*([^\r\n]{1,120})", re.IGNORECASE)
DATE_PATTERN = re.compile(r"date\s*[:#-]?\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})", re.IGNORECASE)
CONTRACTOR_PATTERN = re.compile(r"contractor(?:'s\s*name)?\s*[:#-]?\s*([^\r\n]{1,120})", re.IGNORECASE)
JOB_PATTERN = re.compile(r"job\s*[:#-]?\s*([^\r\n]{1,120})", re.IGNORECASE)
JOB_LOCATION_PATTERN = re.compile(r"job\s*location\s*[:#-]?\s*([^\r\n]{1,120})", re.IGNORECASE)
COMPANY_HAULING_FOR_PATTERN = re.compile(r"company\s+hauling\s+for\s*[:#-]?\s*([^\r\n]{1,120})", re.IGNORECASE)
START_TIME_PATTERN = re.compile(r"start\s*time\s*[:#-]?\s*([0-9]{1,2}[:.][0-9]{2}\s*(?:am|pm)?)", re.IGNORECASE)
FINISH_TIME_PATTERN = re.compile(r"finish\s*time\s*[:#-]?\s*([0-9]{1,2}[:.][0-9]{2}\s*(?:am|pm)?)", re.IGNORECASE)
LINE_ITEM_MATERIAL_PATTERN = re.compile(
    r"(?:description|item|product|material)\s*[:#-]?\s*([^\r\n]{2,160})",
    re.IGNORECASE,
)
NET_WEIGHT_PATTERN = re.compile(
    r"(?:net\s*weight|net)\s*[:#-]?\s*([\d,]+(?:\.\d+)?)\s*(?:lb|lbs|pounds)?",
    re.IGNORECASE,
)
GROSS_WEIGHT_PATTERN = re.compile(
    r"(?:gross\s*weight|gross)\s*[:#-]?\s*([\d,]+(?:\.\d+)?)\s*(?:lb|lbs|pounds)?",
    re.IGNORECASE,
)
TARE_WEIGHT_PATTERN = re.compile(
    r"(?:tare\s*weight|tare)\s*[:#-]?\s*([\d,]+(?:\.\d+)?)\s*(?:lb|lbs|pounds)?",
    re.IGNORECASE,
)
LOAD_COUNT_PATTERN = re.compile(r"(?:loads?|load\s*count)\s*[:#-]?\s*(\d+)", re.IGNORECASE)
# "#OF LOADS # 7" (Trucking Beast format)
LOAD_COUNT_HASH_PATTERN = re.compile(r"#\s*of\s*loads?\s*#?\s*(\d+)", re.IGNORECASE)
# "# Loads:\n\n7" — N on line after label (Rodriguez format)
LOAD_COUNT_NEXTLINE_PATTERN = re.compile(r"#?\s*loads?\s*[:#-]?\s*[\r\n]+\s*(\d{1,3})\b", re.IGNORECASE)
LOAD_COUNT_REVERSED_PATTERN = re.compile(r"\b(\d{1,3})\s*loads?\b", re.IGNORECASE)
LOAD_COUNT_REVERSED_ABBREV_PATTERN = re.compile(r"\b(\d{1,3})\s*lds?\b", re.IGNORECASE)
SPECIAL_COMMENTS_PATTERN = re.compile(r"(?:special\s+hauls?\s+or\s+comments?|notes?)\s*[:#-]?\s*([^\r\n]{1,160})", re.IGNORECASE)
QUANTITY_PATTERN = re.compile(r"(?:qty|quantity)\s*[:#-]?\s*(\d+)", re.IGNORECASE)
# "OPERATORS NAME" / "OPERATOR:" as driver fallback
OPERATOR_PATTERN = re.compile(r"operator'?s?\s*(?:name)?\s*[:#-]?\s*([^\r\n]{2,80})", re.IGNORECASE)
# Truck # with possible comma/punctuation noise: "Truck #:, MJ-11"
TRUCK_HASH_PATTERN = re.compile(r"truck\s*#\s*[:#,.-]*\s*([A-Za-z0-9][A-Za-z0-9-]{0,30})", re.IGNORECASE)
# P&J: JOB NUMBER# 16065 → ticket_number
JOB_NUMBER_AS_TICKET_PATTERN = re.compile(r"job\s*(?:number|no\.?)\s*#?\s*[:#-]?\s*(\d{4,6})", re.IGNORECASE)
# MATERIAL SUPPLY (P&J slips)
MATERIAL_SUPPLY_PATTERN = re.compile(r"material\s+supply\s*[:#-]?\s*([^\r\n]{1,120})", re.IGNORECASE)
# Circled product via OCR parentheses: "(DIRT)"
PRODUCT_CIRCLED_PATTERN = re.compile(r"\((MILLING|STONE|MUD|ROUGH|ABC|ASPHALT|DIRT|CONCRETE|ROCKS|DEBRIS)\)", re.IGNORECASE)
# Truck size circled: "(QUAD)" or "(QUAD-AXLE)"
TRUCK_SIZE_CIRCLED_PATTERN = re.compile(r"\(?(TANDEM|TRI-?AXLE|QUAD(?:-AXLE)?|QUINT(?:-AXLE)?)\)?", re.IGNORECASE)
# Foreman signature line load count: "13 loads"
FOREMAN_LOAD_PATTERN = re.compile(r"foreman'?s?\s+signature[^\r\n]*?(\d{1,3})\s*(?:loads?|lds?)\b", re.IGNORECASE)
SHORT_HEADER_TICKET_LINE_PATTERN = re.compile(r"^\s*(\d{4,6})\s*$")
# Truck IDs must look like an ID: start with letters/digits, short, no long phrases
_TRUCK_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9#. -]{0,24}$")
ENCLOSED_DIGIT_PATTERN = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]")
ENCLOSED_DIGIT_MAP = {
    "①": 1,
    "②": 2,
    "③": 3,
    "④": 4,
    "⑤": 5,
    "⑥": 6,
    "⑦": 7,
    "⑧": 8,
    "⑨": 9,
    "⑩": 10,
    "⑪": 11,
    "⑫": 12,
    "⑬": 13,
    "⑭": 14,
    "⑮": 15,
    "⑯": 16,
    "⑰": 17,
    "⑱": 18,
    "⑲": 19,
    "⑳": 20,
}

COMMON_MATERIAL_TERMS = (
    "dirt",
    "soil",
    "top soil",
    "sand",
    "gravel",
    "aggregate",
    "rock",
    "asphalt",
    "rip rap",
    "base course",
    "stone",
    "milling",
    "concrete",
    "debris",
)

# Words that look like materials in product-list context but are not material names
_MATERIAL_BLOCKLIST = frozenset({
    "hauled", "materials", "supply", "product", "description", "item",
    "hauling", "haul", "demolition",
})

# Words that indicate a captured value is actually a form field label, not a material name
_FIELD_LABEL_WORDS = frozenset({
    "location", "equipment", "contractor", "number", "time", "size",
    "tandem", "triaxle", "quad", "quint", "company", "customer",
    "operator", "date", "signature", "foreman", "supervisor", "total",
    "miles", "lunch", "minutes", "hours", "worked",
})


def _is_valid_material_capture(value: str) -> bool:
    """Return False if the captured value looks like an OCR field-label or multi-column concat."""
    if not value or len(value) > 50:
        return False
    if ":" in value:  # field label indicator (e.g. "JOB LOCATION: EQUIPMENT")
        return False
    words = value.lower().split()
    if len(words) > 4:  # real material names are 1-3 words max
        return False
    label_count = sum(1 for w in words if w in _FIELD_LABEL_WORDS)
    if label_count >= 1:  # any field-label word = reject
        return False
    if value.lower().strip() in _MATERIAL_BLOCKLIST:
        return False
    return True

TICKET_SPLIT_PATTERN = re.compile(
    r"(?=\b(?:ticket\s*#|ticket\s*number|ticket\b|invoice\s*(?:number|#|no\.?|num\.)?)\b)",
    re.IGNORECASE,
)
DATE_SPLIT_PATTERN = re.compile(r"(?=\bdate\s*[:#-])", re.IGNORECASE)


def _first_group(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    return match.group(1).strip()


def _normalize_number(value: str) -> str:
    return value.replace(",", "").strip()


def _filename_to_search_text(filename: str) -> str:
    base = filename.strip()
    if not base:
        return ""
    return re.sub(r"[_-]+", " ", base)


def _material_from_terms(text: str) -> str:
    lowered = text.lower()
    for term in COMMON_MATERIAL_TERMS:
        # Match even when embedded in OCR noise like "JADIRT" → "dirt"
        if term in lowered:
            return " ".join(word.capitalize() for word in term.split())
    return ""


def _clean_ticket_like_value(value: str) -> str:
    # Trim punctuation that can trail extracted invoice/ticket references.
    return value.strip().strip(".,;:")


def _invoice_from_filename(original_filename: str) -> str:
    filename = original_filename.strip().lower()
    if "invoice" not in filename:
        return ""

    digits = "".join(re.findall(r"\d", original_filename))
    if len(digits) < 3:
        return ""
    return f"INV-{digits}"


def _header_ticket_from_lines(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:20]:
        match = SHORT_HEADER_TICKET_LINE_PATTERN.match(line)
        if match:
            return match.group(1)
    return ""


def _extract_load_count(text: str) -> str:
    # 1. "#OF LOADS # 7" (Trucking Beast format)
    hash_load = _first_group(LOAD_COUNT_HASH_PATTERN, text)
    if hash_load:
        return hash_load

    # 2. "# Loads:\n\n7" multi-line (Rodriguez format)
    nextline_load = _first_group(LOAD_COUNT_NEXTLINE_PATTERN, text)
    if nextline_load:
        return nextline_load

    # 3. Direct "loads: N"
    direct = _first_group(LOAD_COUNT_PATTERN, text)
    if direct:
        return direct

    # 4. "N loads" anywhere
    reversed_full = _first_group(LOAD_COUNT_REVERSED_PATTERN, text)
    if reversed_full:
        return reversed_full

    # 5. "N Lds" abbreviation
    reversed_abbrev = _first_group(LOAD_COUNT_REVERSED_ABBREV_PATTERN, text)
    if reversed_abbrev:
        return reversed_abbrev

    # 6. Notes/special-comments line: "6 Lds", "7 loads"
    comments_text = _first_group(SPECIAL_COMMENTS_PATTERN, text)
    if comments_text:
        comments_load = _first_group(LOAD_COUNT_REVERSED_PATTERN, comments_text) or _first_group(
            LOAD_COUNT_REVERSED_ABBREV_PATTERN, comments_text
        )
        if comments_load:
            return comments_load

    # 7. Foreman's signature line written load count: "13 loads"
    foreman_load = _first_group(FOREMAN_LOAD_PATTERN, text)
    if foreman_load:
        return foreman_load

    # 8. Unicode enclosed circled digits
    enclosed_digits = [ENCLOSED_DIGIT_MAP[symbol] for symbol in ENCLOSED_DIGIT_PATTERN.findall(text)]
    if enclosed_digits:
        return str(max(enclosed_digits))

    return _first_group(QUANTITY_PATTERN, text)


def _is_valid_invoice_reference(value: str) -> bool:
    if len(value) < 3:
        return False
    return bool(re.search(r"\d", value))


def _extract_fields_from_text(
    text: str,
    *,
    original_filename: str,
    allow_filename_ticket_fallback: bool,
) -> dict[str, str]:
    # Prefer TRUCK_HASH_PATTERN for "Truck #:, MJ-11" noise; fall back to general TRUCK_PATTERN
    truck_raw = _first_group(TRUCK_HASH_PATTERN, text) or _first_group(TRUCK_PATTERN, text)
    truck_clean = re.sub(r"^[^A-Za-z0-9]+", "", truck_raw).strip() if truck_raw else ""
    # Discard truck values that are clearly noise (long phrases, special chars)
    if truck_clean and not _TRUCK_ID_PATTERN.match(truck_clean):
        truck_clean = ""

    fields = {
        "ticket_number": _clean_ticket_like_value(_first_group(TICKET_NUMBER_PATTERN, text)),
        "date": _first_group(DATE_PATTERN, text),
        "contractor": _first_group(CONTRACTOR_PATTERN, text),
        "driver": _first_group(DRIVER_PATTERN, text),
        "truck": truck_clean,
        "job": _first_group(JOB_PATTERN, text),
        "job_location": _first_group(JOB_LOCATION_PATTERN, text),
        "company_hauling_for": _first_group(COMPANY_HAULING_FOR_PATTERN, text),
        "start_time": _first_group(START_TIME_PATTERN, text),
        "finish_time": _first_group(FINISH_TIME_PATTERN, text),
        "material": _first_group(MATERIAL_PATTERN, text),
        "net_weight_lbs": _normalize_number(_first_group(NET_WEIGHT_PATTERN, text)),
        "gross_weight_lbs": _normalize_number(_first_group(GROSS_WEIGHT_PATTERN, text)),
        "tare_weight_lbs": _normalize_number(_first_group(TARE_WEIGHT_PATTERN, text)),
        "number_of_loads": _extract_load_count(text),
    }

    # OPERATORS NAME as driver fallback (Trucking Beast format)
    if not fields["driver"]:
        operator = _first_group(OPERATOR_PATTERN, text).strip()
        if operator and len(operator) > 1:
            fields["driver"] = operator

    # P&J: JOB NUMBER# 16065 → ticket_number
    if not fields["ticket_number"]:
        job_num = _first_group(JOB_NUMBER_AS_TICKET_PATTERN, text)
        if job_num:
            fields["ticket_number"] = job_num

    if not fields["ticket_number"]:
        invoice_candidate = _clean_ticket_like_value(_first_group(INVOICE_NUMBER_PATTERN, text))
        if _is_valid_invoice_reference(invoice_candidate):
            fields["ticket_number"] = invoice_candidate

    if not fields["ticket_number"]:
        header_ticket = _header_ticket_from_lines(text)
        if header_ticket:
            fields["ticket_number"] = header_ticket

    if allow_filename_ticket_fallback and not fields["ticket_number"]:
        fields["ticket_number"] = _invoice_from_filename(original_filename)

    # Material supply (P&J slips) → material
    if not fields["material"]:
        fields["material"] = _first_group(MATERIAL_SUPPLY_PATTERN, text)
    # Circled product via OCR: "(DIRT)"
    if not fields["material"]:
        circled = _first_group(PRODUCT_CIRCLED_PATTERN, text)
        if circled:
            fields["material"] = circled.capitalize()
    # Material resolution cascade — validate each capture before accepting
    if not fields["material"]:
        ms = _first_group(MATERIAL_SUPPLY_PATTERN, text)
        if _is_valid_material_capture(ms):
            fields["material"] = ms
    if not fields["material"]:
        circled = _first_group(PRODUCT_CIRCLED_PATTERN, text)
        if circled:
            fields["material"] = circled.capitalize()
    if not fields["material"]:
        line_item = _first_group(LINE_ITEM_MATERIAL_PATTERN, text)
        if _is_valid_material_capture(line_item):
            fields["material"] = line_item
    if not fields["material"]:
        fields["material"] = _material_from_terms(text)
    # Final blocklist / validation filter
    if fields.get("material") and not _is_valid_material_capture(fields["material"]):
        del fields["material"]
        fields["material"] = _material_from_terms(text)

    return {key: value for key, value in fields.items() if value}


def _split_ticket_blocks(raw_text: str) -> list[str]:
    text = raw_text.strip()
    if not text:
        return []

    blocks: list[str] = []
    pages = [page.strip() for page in text.split("\f") if page.strip()]
    if pages:
        blocks.extend(pages)
    else:
        blocks.append(text)

    expanded_blocks: list[str] = []
    for block in blocks:
        split_parts = [part.strip() for part in TICKET_SPLIT_PATTERN.split(block) if part.strip()]
        if len(split_parts) <= 1:
            date_parts = [part.strip() for part in DATE_SPLIT_PATTERN.split(block) if part.strip()]
            if len(date_parts) > 1:
                expanded_blocks.extend(date_parts)
            else:
                expanded_blocks.append(block)
        else:
            expanded_blocks.extend(split_parts)

    return expanded_blocks


def extract_ticket_candidates(raw_text: str, *, original_filename: str = "") -> list[dict[str, str]]:
    text = raw_text.strip()
    filename_text = _filename_to_search_text(original_filename)
    if not text and not filename_text:
        return []

    candidates: list[dict[str, str]] = []
    blocks = _split_ticket_blocks(text) if text else []
    for block in blocks:
        candidate = _extract_fields_from_text(
            block,
            original_filename=original_filename,
            allow_filename_ticket_fallback=False,
        )
        if not candidate:
            continue
        candidates.append(candidate)

    if not candidates:
        fallback_text = "\n".join(part for part in [text, filename_text] if part).strip()
        candidate = _extract_fields_from_text(
            fallback_text,
            original_filename=original_filename,
            allow_filename_ticket_fallback=True,
        )
        if candidate:
            candidates.append(candidate)

    unique: list[dict[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for candidate in candidates:
        key = tuple(sorted(candidate.items()))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)

    return unique


def extract_ticket_preview(raw_text: str, *, original_filename: str = "") -> tuple[dict[str, str], str, float]:
    """Return light-weight ticket signals from extracted text.

    This is intentionally deterministic and cheap so we can run it during upload.
    """
    candidates = extract_ticket_candidates(raw_text, original_filename=original_filename)
    if not candidates:
        return {}, "", 0.0

    entities = candidates[0]

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

    llm_summary = summarize_ticket_preview(
        raw_text,
        entities=entities,
        original_filename=original_filename,
    )
    if llm_summary:
        summary = llm_summary

    return entities, summary, confidence
