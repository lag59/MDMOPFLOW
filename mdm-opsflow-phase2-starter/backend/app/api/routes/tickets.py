from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import json
import re

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import MaterialDensityPreset, Ticket
from app.schemas import (
    TicketCalculatorPrefillResponse,
    MaterialDensityPresetResponse,
    MaterialDensityPresetUpsertRequest,
    TicketCreate,
    TicketQuantityCalculationRequest,
    TicketQuantityCalculationResponse,
    TicketResponse,
    TicketUploadExtractionItemResponse,
    TicketUploadExtractionResponse,
    TicketUpdate,
)
from app.services.intake_processing import process_intake_upload
from app.services.ticket_extractor import extract_ticket_candidates


router = APIRouter(prefix="/api/tickets", tags=["Tickets"])

WEIGHT_LBS_PER_TON = Decimal("2000")

# Default truck capacities in tons per load
TRUCK_TYPE_CAPACITY: dict[str, Decimal] = {
    "tandem": Decimal("18"),
    "triaxle": Decimal("22"),
    "tri-axle": Decimal("22"),
    "quad": Decimal("22"),
    "quad-axle": Decimal("22"),
    "quint": Decimal("26"),
    "quint-axle": Decimal("26"),
}


def _resolve_truck_capacity(truck_type: str | None, explicit_capacity: Decimal | None) -> tuple[Decimal | None, str | None]:
    """Return (capacity, resolved_type). Explicit capacity always wins."""
    if explicit_capacity is not None:
        label = truck_type.strip().lower() if truck_type else "custom"
        return explicit_capacity, label

    if truck_type:
        key = truck_type.strip().lower()
        capacity = TRUCK_TYPE_CAPACITY.get(key)
        if capacity:
            return capacity, key

    return None, None


def _round_2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _safe_divide(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _normalize_material_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_ticket_number(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _canonicalize_ticket_number(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_ticket_number(value))


def _build_extracted_text_preview(extracted_text: str, *, max_chars: int = 2400) -> str | None:
    normalized = (extracted_text or "").strip()
    if not normalized:
        return None

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    if not lines:
        return None

    focus_patterns = (
        "load",
        "tally",
        "qty",
        "quantity",
        "circle",
        "ticket",
        "weight",
    )
    focused_lines = [line for line in lines if any(pattern in line.lower() for pattern in focus_patterns)]

    preview_parts: list[str] = []
    if focused_lines:
        preview_parts.append("Key lines for review:")
        preview_parts.extend(focused_lines[:12])
        preview_parts.append("")

    preview_parts.append("OCR/Text preview:")
    preview_parts.extend(lines[:35])
    preview = "\n".join(preview_parts).strip()
    return preview[:max_chars]


def _find_duplicate_ticket(
    db: Session,
    *,
    tenant_id: str,
    ticket_number: str,
    exclude_ticket_id: str | None = None,
) -> Ticket | None:
    canonical = _canonicalize_ticket_number(ticket_number)
    if not canonical:
        return None

    candidates = db.scalars(select(Ticket).where(Ticket.tenant_id == tenant_id)).all()
    for candidate in candidates:
        if exclude_ticket_id and candidate.id == exclude_ticket_id:
            continue
        if _canonicalize_ticket_number(candidate.ticket_number or "") == canonical:
            return candidate
    return None


def _find_density_preset(
    db: Session,
    *,
    tenant_id: str,
    material_name: str,
) -> MaterialDensityPreset | None:
    normalized = _normalize_material_name(material_name)
    presets = db.scalars(
        select(MaterialDensityPreset).where(MaterialDensityPreset.tenant_id == tenant_id)
    ).all()
    for preset in presets:
        if _normalize_material_name(preset.material_name) == normalized:
            return preset
    return None


def _standardize_ticket_payload(
    *,
    values: dict[str, Decimal | str | None],
    db: Session,
    tenant_id: str,
) -> None:
    weight = values.get("weight")
    tons = values.get("tons")
    volume_yards = values.get("volume_yards")
    material = values.get("material")

    if tons is None and isinstance(weight, Decimal):
        values["tons"] = _round_2(weight / WEIGHT_LBS_PER_TON)
        tons = values.get("tons")

    if volume_yards is None and isinstance(tons, Decimal) and isinstance(material, str) and material.strip():
        preset = _find_density_preset(db, tenant_id=tenant_id, material_name=material)
        if preset and preset.density_tons_per_cubic_yard and Decimal(str(preset.density_tons_per_cubic_yard)) > 0:
            density = Decimal(str(preset.density_tons_per_cubic_yard))
            calculated_yards = _safe_divide(tons, density)
            if calculated_yards is not None:
                values["volume_yards"] = _round_2(calculated_yards)


def _decimal_from_string(value: str | None) -> Decimal | None:
    if value is None:
        return None
    normalized = value.strip().replace(",", "")
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except Exception:
        return None


def _int_from_string(value: str | None) -> int | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return int(normalized)
    except Exception:
        return None


@router.get(
    "/material-density-presets",
    response_model=list[MaterialDensityPresetResponse],
    operation_id="tickets_material_density_presets_list",
    summary="List tenant material density presets",
)
def list_material_density_presets(
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    return db.scalars(
        select(MaterialDensityPreset)
        .where(MaterialDensityPreset.tenant_id == tenant_id)
        .order_by(MaterialDensityPreset.material_name.asc())
    ).all()


@router.put(
    "/material-density-presets/{material_name}",
    response_model=MaterialDensityPresetResponse,
    operation_id="tickets_material_density_presets_upsert",
    summary="Create or update a tenant material density preset",
)
def upsert_material_density_preset(
    material_name: str,
    payload: MaterialDensityPresetUpsertRequest,
    context: RequestContext = Depends(require_permissions("intake_write")),
    db: Session = Depends(get_db),
):
    normalized_material_name = material_name.strip()
    if not normalized_material_name:
        raise HTTPException(status_code=400, detail="material_name is required")

    tenant_id = _tenant_id_from_context(context)
    existing = _find_density_preset(db, tenant_id=tenant_id, material_name=normalized_material_name)
    if existing:
        existing.material_name = normalized_material_name
        existing.density_tons_per_cubic_yard = payload.density_tons_per_cubic_yard
        db.commit()
        db.refresh(existing)
        return existing

    preset = MaterialDensityPreset(
        tenant_id=tenant_id,
        material_name=normalized_material_name,
        density_tons_per_cubic_yard=payload.density_tons_per_cubic_yard,
        created_by=context.user.id,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@router.delete(
    "/material-density-presets/{material_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="tickets_material_density_presets_delete",
    summary="Delete a tenant material density preset",
)
def delete_material_density_preset(
    material_name: str,
    context: RequestContext = Depends(require_permissions("intake_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    existing = _find_density_preset(db, tenant_id=tenant_id, material_name=material_name)
    if not existing:
        raise HTTPException(status_code=404, detail="Material density preset not found")
    db.delete(existing)
    db.commit()


def _tenant_id_from_context(context: RequestContext) -> str:
    if context.tenant_id:
        return context.tenant_id
    if context.membership:
        return context.membership.tenant_id
    raise HTTPException(status_code=400, detail="X-Tenant-ID is required for platform admins")


@router.post(
    "/upload-extract",
    response_model=TicketUploadExtractionResponse,
    operation_id="tickets_upload_extract",
    summary="Upload ticket files for extraction and calculator prefill",
)
async def upload_extract_tickets(
    files: list[UploadFile] = File(...),
    create_tickets: bool = Query(default=False),
    context: RequestContext = Depends(require_permissions("intake_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    items: list[TicketUploadExtractionItemResponse] = []

    for file in files:
        payload = await file.read()
        if not payload:
            continue

        processed = process_intake_upload(
            tenant_id=tenant_id,
            original_filename=file.filename or "upload.bin",
            mime_type=file.content_type or "application/octet-stream",
            payload=payload,
        )

        extracted_entities_raw = json.loads(processed.extracted_entities or "{}")
        fallback_entities = {str(key): str(value) for key, value in extracted_entities_raw.items()}
        extracted_candidates = extract_ticket_candidates(
            processed.extracted_text,
            original_filename=processed.original_filename,
        )
        candidate_entities_list = extracted_candidates or ([fallback_entities] if fallback_entities else [])
        if not candidate_entities_list:
            candidate_entities_list = [{}]

        for extracted_entities in candidate_entities_list:
            created_ticket_id: str | None = None
            duplicate_ticket_id: str | None = None
            ticket_number = extracted_entities.get("ticket_number", "").strip()
            if create_tickets and ticket_number:
                duplicate = _find_duplicate_ticket(
                    db,
                    tenant_id=tenant_id,
                    ticket_number=ticket_number,
                )
                if duplicate is not None:
                    duplicate_ticket_id = duplicate.id
                else:
                    create_values: dict[str, Decimal | str | None] = {
                        "weight": _decimal_from_string(extracted_entities.get("net_weight_lbs")),
                        "tons": None,
                        "volume_yards": None,
                        "material": extracted_entities.get("material", "").strip(),
                    }
                    _standardize_ticket_payload(values=create_values, db=db, tenant_id=tenant_id)

                    ticket = Ticket(
                        tenant_id=tenant_id,
                        intake_item_id=None,
                        project_id=None,
                        ticket_number=ticket_number,
                        truck=extracted_entities.get("truck", "").strip(),
                        driver=extracted_entities.get("driver", "").strip(),
                        material=extracted_entities.get("material", "").strip(),
                        origin="",
                        destination="",
                        weight=create_values.get("weight"),
                        tons=create_values.get("tons"),
                        volume_yards=create_values.get("volume_yards"),
                        status="draft",
                        notes="Auto-created from ticket file extraction.",
                        source_document_path=processed.file_path,
                        created_by=context.user.id,
                    )
                    db.add(ticket)
                    db.flush()
                    created_ticket_id = ticket.id

            items.append(
                TicketUploadExtractionItemResponse(
                    filename=processed.filename,
                    original_filename=processed.original_filename,
                    mime_type=processed.mime_type,
                    file_size_bytes=processed.file_size_bytes,
                    extracted_summary=processed.extracted_summary,
                    extracted_text_preview=_build_extracted_text_preview(processed.extracted_text),
                    extraction_confidence=processed.classification_confidence,
                    review_required=processed.needs_review,
                    extracted_entities=extracted_entities,
                    calculator_prefill=TicketCalculatorPrefillResponse(
                        material_name=extracted_entities.get("material"),
                        gross_weight_lbs=extracted_entities.get("gross_weight_lbs"),
                        tare_weight_lbs=extracted_entities.get("tare_weight_lbs"),
                        net_weight_lbs=extracted_entities.get("net_weight_lbs"),
                        number_of_loads=_int_from_string(extracted_entities.get("number_of_loads")),
                    ),
                    created_ticket_id=created_ticket_id,
                    duplicate_ticket_id=duplicate_ticket_id,
                )
            )

    if create_tickets:
        db.commit()

    return TicketUploadExtractionResponse(items=items)


@router.post(
    "/quantity-calculation",
    response_model=TicketQuantityCalculationResponse,
    operation_id="tickets_quantity_calculation",
    summary="Calculate ticket tons, yards, load metrics, and cost projections",
)
def calculate_ticket_quantities(
    payload: TicketQuantityCalculationRequest,
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    assumptions: list[str] = []
    tenant_id = _tenant_id_from_context(context)

    # ── 1. Net weight from scale (Priority 1: Actual) ──────────────────────
    net_weight_lbs = payload.net_weight_lbs
    if net_weight_lbs is None and payload.gross_weight_lbs is not None and payload.tare_weight_lbs is not None:
        net_weight_lbs = payload.gross_weight_lbs - payload.tare_weight_lbs
        assumptions.append("net_weight_lbs derived from gross_weight_lbs - tare_weight_lbs")

    if net_weight_lbs is not None and net_weight_lbs < 0:
        raise HTTPException(status_code=400, detail="net_weight_lbs cannot be negative")

    net_tons: Decimal | None = None
    if net_weight_lbs is not None:
        net_tons = net_weight_lbs / WEIGHT_LBS_PER_TON

    # ── 2. Truck type / capacity resolution ───────────────────────────────
    resolved_truck_capacity, resolved_truck_type = _resolve_truck_capacity(
        payload.truck_type, payload.truck_capacity_tons
    )
    if resolved_truck_capacity and resolved_truck_type and payload.truck_capacity_tons is None and payload.truck_type:
        assumptions.append(f"truck_capacity_tons resolved from truck_type '{resolved_truck_type}' default ({resolved_truck_capacity} tons/load)")

    # ── 3. Number of loads ────────────────────────────────────────────────
    load_count: Decimal | None = None
    if payload.number_of_loads is not None:
        if payload.number_of_loads <= 0:
            raise HTTPException(status_code=400, detail="number_of_loads must be > 0")
        load_count = Decimal(payload.number_of_loads)

    # ── 4. Estimation path: capacity × loads when no scale weight ─────────
    weight_method: str | None = None
    total_tons: Decimal | None = None

    if net_tons is not None:
        weight_method = "actual"
        total_tons = net_tons
    elif resolved_truck_capacity is not None and load_count is not None:
        # No scale weight — estimate from truck capacity × loads
        total_tons = resolved_truck_capacity * load_count
        weight_method = "estimated"
        assumptions.append(
            f"total_tons estimated: {resolved_truck_capacity} tons/load (truck capacity) × {load_count} loads = {_round_2(total_tons)} tons"
        )
        # Derive a representative single-load net_tons for per-load calculations
        net_tons = resolved_truck_capacity

    if total_tons is None and net_tons is not None:
        total_tons = net_tons

    # ── 5. Density / material ─────────────────────────────────────────────
    resolved_density = payload.material_density_tons_per_cubic_yard
    resolved_density_source: str | None = None
    resolved_material_name: str | None = payload.material_name.strip() if payload.material_name else None

    if resolved_density is None and resolved_material_name:
        preset = _find_density_preset(db, tenant_id=tenant_id, material_name=resolved_material_name)
        if preset:
            resolved_density = Decimal(str(preset.density_tons_per_cubic_yard))
            resolved_material_name = preset.material_name
            resolved_density_source = "preset"
            assumptions.append("material_density_tons_per_cubic_yard resolved from tenant material preset")

    if resolved_density is not None and resolved_density <= 0:
        raise HTTPException(status_code=400, detail="material_density_tons_per_cubic_yard must be > 0")

    if resolved_density is not None and resolved_density_source is None:
        resolved_density_source = "request"

    # ── 6. Volume calculations ────────────────────────────────────────────
    # Per-load volume uses net_tons (single load weight)
    per_load_yards: Decimal | None = None
    if net_tons is not None and resolved_density is not None:
        per_load_yards = _safe_divide(net_tons, resolved_density)

    # Total volume uses total_tons
    total_cubic_yards: Decimal | None = None
    if total_tons is not None and resolved_density is not None:
        total_cubic_yards = _safe_divide(total_tons, resolved_density)

    # estimated_cubic_yards kept for backwards-compat (= total when loads provided, per-load otherwise)
    estimated_cubic_yards = total_cubic_yards if total_cubic_yards is not None else per_load_yards

    # ── 7. Per-load stats ─────────────────────────────────────────────────
    estimated_load_count: Decimal | None = load_count
    if estimated_load_count is None and resolved_truck_capacity is not None and net_tons is not None:
        estimated_load_count = _safe_divide(net_tons, resolved_truck_capacity)
        assumptions.append("estimated_load_count derived from net_tons / truck_capacity_tons")

    tons_per_load: Decimal | None = None
    cubic_yards_per_load: Decimal | None = None
    if load_count is not None and load_count > 0:
        if total_tons is not None:
            tons_per_load = _safe_divide(total_tons, load_count)
        if total_cubic_yards is not None:
            cubic_yards_per_load = _safe_divide(total_cubic_yards, load_count)
    elif per_load_yards is not None:
        cubic_yards_per_load = per_load_yards
        if net_tons is not None:
            tons_per_load = net_tons

    # ── 8. Cost ───────────────────────────────────────────────────────────
    cost_from_ton: Decimal | None = None
    cost_from_yard: Decimal | None = None
    cost_from_load: Decimal | None = None
    if payload.rate_per_ton is not None and total_tons is not None:
        cost_from_ton = payload.rate_per_ton * total_tons
    if payload.rate_per_cubic_yard is not None and total_cubic_yards is not None:
        cost_from_yard = payload.rate_per_cubic_yard * total_cubic_yards
    if payload.rate_per_load is not None:
        load_basis = load_count if load_count is not None else estimated_load_count
        if load_basis is not None:
            cost_from_load = payload.rate_per_load * load_basis

    selected_cost_method: str | None = None
    selected_total_cost: Decimal | None = None
    if cost_from_ton is not None:
        selected_cost_method = "per_ton"
        selected_total_cost = cost_from_ton
    elif cost_from_yard is not None:
        selected_cost_method = "per_cubic_yard"
        selected_total_cost = cost_from_yard
    elif cost_from_load is not None:
        selected_cost_method = "per_load"
        selected_total_cost = cost_from_load

    return TicketQuantityCalculationResponse(
        net_weight_lbs=_round_2(net_weight_lbs) if net_weight_lbs is not None else None,
        net_tons=_round_2(net_tons) if net_tons is not None else None,
        total_tons=_round_2(total_tons) if total_tons is not None else None,
        total_cubic_yards=_round_2(total_cubic_yards) if total_cubic_yards is not None else None,
        estimated_cubic_yards=_round_2(estimated_cubic_yards) if estimated_cubic_yards is not None else None,
        estimated_load_count=_round_2(estimated_load_count) if estimated_load_count is not None else None,
        tons_per_load=_round_2(tons_per_load) if tons_per_load is not None else None,
        cubic_yards_per_load=_round_2(cubic_yards_per_load) if cubic_yards_per_load is not None else None,
        cost_from_ton=_round_2(cost_from_ton) if cost_from_ton is not None else None,
        cost_from_cubic_yard=_round_2(cost_from_yard) if cost_from_yard is not None else None,
        cost_from_load=_round_2(cost_from_load) if cost_from_load is not None else None,
        selected_cost_method=selected_cost_method,
        selected_total_cost=_round_2(selected_total_cost) if selected_total_cost is not None else None,
        resolved_material_name=resolved_material_name,
        resolved_density_source=resolved_density_source,
        weight_method=weight_method,
        resolved_truck_type=resolved_truck_type,
        resolved_truck_capacity_tons=_round_2(resolved_truck_capacity) if resolved_truck_capacity is not None else None,
        assumptions=assumptions,
    )

    net_weight_lbs = payload.net_weight_lbs
    if net_weight_lbs is None and payload.gross_weight_lbs is not None and payload.tare_weight_lbs is not None:
        net_weight_lbs = payload.gross_weight_lbs - payload.tare_weight_lbs
        assumptions.append("net_weight_lbs derived from gross_weight_lbs - tare_weight_lbs")

    if net_weight_lbs is not None and net_weight_lbs < 0:
        raise HTTPException(status_code=400, detail="net_weight_lbs cannot be negative")

    net_tons: Decimal | None = None
    if net_weight_lbs is not None:
        net_tons = net_weight_lbs / WEIGHT_LBS_PER_TON

    resolved_density = payload.material_density_tons_per_cubic_yard
    resolved_density_source: str | None = None
    resolved_material_name: str | None = payload.material_name.strip() if payload.material_name else None

    if resolved_density is None and resolved_material_name:
        preset = _find_density_preset(db, tenant_id=tenant_id, material_name=resolved_material_name)
        if preset:
            resolved_density = Decimal(str(preset.density_tons_per_cubic_yard))
            resolved_material_name = preset.material_name
            resolved_density_source = "preset"
            assumptions.append("material_density_tons_per_cubic_yard resolved from tenant material preset")

    if resolved_density is not None and resolved_density <= 0:
        raise HTTPException(status_code=400, detail="material_density_tons_per_cubic_yard must be > 0")

    if resolved_density is not None and resolved_density_source is None:
        resolved_density_source = "request"

    estimated_cubic_yards: Decimal | None = None
    if net_tons is not None and resolved_density is not None:
        estimated_cubic_yards = _safe_divide(net_tons, resolved_density)

    estimated_load_count: Decimal | None = None
    if payload.number_of_loads is not None:
        if payload.number_of_loads <= 0:
            raise HTTPException(status_code=400, detail="number_of_loads must be > 0")
        estimated_load_count = Decimal(payload.number_of_loads)
    elif payload.truck_capacity_tons is not None and net_tons is not None:
        if payload.truck_capacity_tons <= 0:
            raise HTTPException(status_code=400, detail="truck_capacity_tons must be > 0")
        estimated_load_count = _safe_divide(net_tons, payload.truck_capacity_tons)
        assumptions.append("estimated_load_count derived from net_tons / truck_capacity_tons")

    tons_per_load: Decimal | None = None
    cubic_yards_per_load: Decimal | None = None
    if estimated_load_count is not None and estimated_load_count > 0:
        if net_tons is not None:
            tons_per_load = _safe_divide(net_tons, estimated_load_count)
        if estimated_cubic_yards is not None:
            cubic_yards_per_load = _safe_divide(estimated_cubic_yards, estimated_load_count)

    cost_from_ton: Decimal | None = None
    cost_from_yard: Decimal | None = None
    cost_from_load: Decimal | None = None
    if payload.rate_per_ton is not None and net_tons is not None:
        cost_from_ton = payload.rate_per_ton * net_tons
    if payload.rate_per_cubic_yard is not None and estimated_cubic_yards is not None:
        cost_from_yard = payload.rate_per_cubic_yard * estimated_cubic_yards
    if payload.rate_per_load is not None and estimated_load_count is not None:
        cost_from_load = payload.rate_per_load * estimated_load_count

    selected_cost_method: str | None = None
    selected_total_cost: Decimal | None = None
    if cost_from_ton is not None:
        selected_cost_method = "per_ton"
        selected_total_cost = cost_from_ton
    elif cost_from_yard is not None:
        selected_cost_method = "per_cubic_yard"
        selected_total_cost = cost_from_yard
    elif cost_from_load is not None:
        selected_cost_method = "per_load"
        selected_total_cost = cost_from_load

    return TicketQuantityCalculationResponse(
        net_weight_lbs=_round_2(net_weight_lbs) if net_weight_lbs is not None else None,
        net_tons=_round_2(net_tons) if net_tons is not None else None,
        estimated_cubic_yards=_round_2(estimated_cubic_yards) if estimated_cubic_yards is not None else None,
        estimated_load_count=_round_2(estimated_load_count) if estimated_load_count is not None else None,
        tons_per_load=_round_2(tons_per_load) if tons_per_load is not None else None,
        cubic_yards_per_load=_round_2(cubic_yards_per_load) if cubic_yards_per_load is not None else None,
        cost_from_ton=_round_2(cost_from_ton) if cost_from_ton is not None else None,
        cost_from_cubic_yard=_round_2(cost_from_yard) if cost_from_yard is not None else None,
        cost_from_load=_round_2(cost_from_load) if cost_from_load is not None else None,
        selected_cost_method=selected_cost_method,
        selected_total_cost=_round_2(selected_total_cost) if selected_total_cost is not None else None,
        resolved_material_name=resolved_material_name,
        resolved_density_source=resolved_density_source,
        assumptions=assumptions,
    )


@router.get(
    "",
    response_model=list[TicketResponse],
    operation_id="tickets_list",
    summary="List tickets",
)
def list_tickets(
    tenant_id: str | None = Query(default=None),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    if "*" in context.permissions:
        if tenant_id:
            return db.scalars(select(Ticket).where(Ticket.tenant_id == tenant_id)).all()
        return db.scalars(select(Ticket)).all()

    assert context.membership is not None
    return db.scalars(select(Ticket).where(Ticket.tenant_id == context.membership.tenant_id)).all()


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="tickets_create",
    summary="Create ticket",
)
def create_ticket(
    payload: TicketCreate,
    context: RequestContext = Depends(require_permissions("intake_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    payload_values = payload.model_dump()
    ticket_number = (payload_values.get("ticket_number") or "").strip()
    if ticket_number:
        duplicate = _find_duplicate_ticket(
            db,
            tenant_id=tenant_id,
            ticket_number=ticket_number,
        )
        if duplicate is not None:
            raise HTTPException(status_code=409, detail=f"Duplicate ticket number detected: {ticket_number}")

    _standardize_ticket_payload(values=payload_values, db=db, tenant_id=tenant_id)

    ticket = Ticket(
        tenant_id=tenant_id,
        intake_item_id=payload_values["intake_item_id"],
        project_id=payload_values["project_id"],
        ticket_number=payload_values["ticket_number"],
        truck=payload_values["truck"],
        driver=payload_values["driver"],
        material=payload_values["material"],
        origin=payload_values["origin"],
        destination=payload_values["destination"],
        load_time=payload_values["load_time"],
        unload_time=payload_values["unload_time"],
        miles=payload_values["miles"],
        weight=payload_values["weight"],
        volume_yards=payload_values["volume_yards"],
        tons=payload_values["tons"],
        fuel_cost=payload_values["fuel_cost"],
        revenue=payload_values["revenue"],
        status=payload_values["status"],
        notes=payload_values["notes"],
        created_by=context.user.id,
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    operation_id="tickets_get",
    summary="Get ticket",
)
def get_ticket(
    ticket_id: str,
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if "*" not in context.permissions and (
        not context.membership or ticket.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    operation_id="tickets_update",
    summary="Update ticket",
)
def update_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    context: RequestContext = Depends(require_permissions("intake_write")),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if "*" not in context.permissions and (
        not context.membership or ticket.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Ticket not found")

    updates = payload.model_dump(exclude_unset=True)
    proposed_ticket_number = updates.get("ticket_number", ticket.ticket_number)
    if isinstance(proposed_ticket_number, str) and proposed_ticket_number.strip():
        duplicate = _find_duplicate_ticket(
            db,
            tenant_id=ticket.tenant_id,
            ticket_number=proposed_ticket_number,
            exclude_ticket_id=ticket.id,
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Duplicate ticket number detected: {proposed_ticket_number.strip()}",
            )

    merged_values = {
        "weight": updates.get("weight", ticket.weight),
        "tons": updates.get("tons", ticket.tons),
        "volume_yards": updates.get("volume_yards", ticket.volume_yards),
        "material": updates.get("material", ticket.material),
    }
    _standardize_ticket_payload(values=merged_values, db=db, tenant_id=ticket.tenant_id)
    for key in ("weight", "tons", "volume_yards"):
        if key not in updates and merged_values.get(key) is not None:
            updates[key] = merged_values[key]

    for key, value in updates.items():
        setattr(ticket, key, value)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="tickets_delete",
    summary="Delete ticket",
)
def delete_ticket(
    ticket_id: str,
    context: RequestContext = Depends(require_permissions("intake_write")),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if "*" not in context.permissions and (
        not context.membership or ticket.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Ticket not found")

    db.delete(ticket)
    db.commit()
