from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import re
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions, resolve_tenant_scope
from app.models import (
    AuditLog,
    IngestionBatch,
    IngestionBatchStatus,
    IntakeItem,
    IntakeStatus,
    IntegrationEvent,
    Ticket,
    User,
)
from app.schemas import (
    IntakeConflictResolveRequest,
    IntakeConflictSuggestionListResponse,
    IntakeConflictSuggestionResponse,
    IntakeConflictValueCandidateResponse,
    IntakeDuplicateResolutionRequest,
    IntakeIntegrationEventProcessRequest,
    IntakeIntegrationEventReplayRequest,
    IntakeReplayExportTokenAuditEntryResponse,
    IntakeReplayExportTokenAuditHistoryListResponse,
    IntakeReplayExportTokenAuditSummaryResponse,
    IntakeReplayExportTokenAuditTrendBucketResponse,
    IntakeReplayExportTokenAuditTrendResponse,
    IntakeReplayExportTokenBulkRevokeActiveRequest,
    IntakeReplayExportTokenBulkRevokeActiveResponse,
    IntakeReplayExportTokenStateAlertsResponse,
    IntakeReplayExportTokenActorStateSummaryResponse,
    IntakeReplayExportTokenStateListResponse,
    IntakeReplayExportTokenStateResponse,
    IntakeReplayExportTokenStateSummaryResponse,
    IntakeReplayExportTokenRevokeRequest,
    IntakeReplayExportTokenRevokeResponse,
    IntakeReplayExportTokenResponse,
    IntakeReplayAuditEntryResponse,
    IntakeIntegrationEventRetryRequest,
    IntakeIntegrationEventResponse,
    IntakeItemResponse,
    IntakePlacementSuggestionListResponse,
    IntakePlacementSuggestionRequest,
    IntakePlacementSuggestionResponse,
)
from app.security import TokenError, create_token, decode_token
from app.core.config import settings
from app.services.canonical_intake import build_canonical_document, score_canonical_document
from app.services.canonical_conflicts import build_quantity_conflict_suggestions
from app.services.intake_placement import suggest_intake_placement
from app.services.intake_processing import process_intake_upload
from app.services.ocr_extraction_service import OCRExtractionService


router = APIRouter(prefix="/api/intake", tags=["Intake Hub"])
MAX_INTEGRATION_EVENT_RETRIES = 3
REPLAY_EXPORT_TOKEN_AUDIT_LIMIT_CAP = 100
REPLAY_EXPORT_TOKEN_AUDIT_ACTIONS = (
    "issue_replay_history_export_token",
    "consume_replay_history_export_token",
    "revoke_replay_history_export_token",
)
_TOKEN_ISSUE_DETAILS_PATTERN = re.compile(r"event_id=(.*?); output=(.*?); limit=(\d+)$")


def _run_extraction_background(item_id: str, tenant_id: str, user_id: str) -> None:
    """Background task: create DocumentExtraction from an IntakeItem after upload.

    Opens its own short-lived DB session so it doesn't share state with the
    upload request session.
    """
    from app.db import SessionLocal
    from uuid import UUID

    db = SessionLocal()
    try:
        service = OCRExtractionService(db, user_id, tenant_id)
        service.trigger_extraction_for_intake(UUID(item_id))
        db.commit()
    except Exception as exc:
        db.rollback()
        # Non-fatal — operator can manually trigger via POST /api/extractions/intake/{id}/extract
        print(f"[extraction-bg] Failed to auto-extract {item_id}: {exc}")
    finally:
        db.close()
MAX_INTEGRATION_EVENT_RETRIES = 3
REPLAY_EXPORT_TOKEN_AUDIT_LIMIT_CAP = 100
REPLAY_EXPORT_TOKEN_AUDIT_ACTIONS = (
    "issue_replay_history_export_token",
    "consume_replay_history_export_token",
    "revoke_replay_history_export_token",
)
_TOKEN_ISSUE_DETAILS_PATTERN = re.compile(r"event_id=(.*?); output=(.*?); limit=(\d+)$")


def _tenant_id_from_context(context: RequestContext) -> str:
    return resolve_tenant_scope(context)


def _ensure_item_access(item: IntakeItem | None, context: RequestContext) -> IntakeItem:
    if not item:
        raise HTTPException(status_code=404, detail="Intake item not found")

    if "*" not in context.permissions and (
        not context.membership or item.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Intake item not found")

    return item


def _add_intake_audit_log(
    db: Session,
    *,
    item: IntakeItem,
    actor_user_id: str,
    action: str,
    details: str,
) -> None:
    db.add(
        AuditLog(
            tenant_id=item.tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type="intake_item",
            resource_id=item.id,
            details=details,
            created_by=actor_user_id,
        )
    )


def _add_integration_event(
    db: Session,
    *,
    tenant_id: str,
    actor_user_id: str,
    event_type: str,
    resource_id: str,
    payload: dict[str, str | int | bool | None],
) -> None:
    db.add(
        IntegrationEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            resource_type="intake_item",
            resource_id=resource_id,
            payload_json=json.dumps(payload),
            status="pending",
            created_by=actor_user_id,
        )
    )


def _should_auto_create_ticket(
    item: IntakeItem,
    *,
    ticket_number: str,
    is_duplicate: bool,
    extracted_entities: dict[str, str],
) -> bool:
    if is_duplicate or not ticket_number:
        return False

    if item.needs_review:
        return False

    if (item.document_type or "").lower() != "ticket":
        return False

    canonical = build_canonical_document(item)
    scores = score_canonical_document(canonical)

    if scores.estimator_document_score >= 0.75:
        return False

    if scores.accounting_document_score >= 0.80:
        return False

    if scores.operational_ticket_score < 0.85:
        return False

    if (item.ocr_status or "").lower() != "completed":
        return False

    if float(item.classification_confidence or 0.0) < 0.75:
        return False

    return True


def _ensure_event_access(event: IntegrationEvent | None, context: RequestContext) -> IntegrationEvent:
    if not event:
        raise HTTPException(status_code=404, detail="Integration event not found")

    if "*" not in context.permissions and (
        not context.membership or event.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Integration event not found")

    return event


@router.get(
    "/items",
    response_model=list[IntakeItemResponse],
    operation_id="intake_items_list",
    summary="List intake items",
)
def list_intake_items(
    tenant_id: str | None = Query(default=None),
    review_queue: bool = Query(default=False),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    query = select(IntakeItem)

    if "*" in context.permissions:
        if tenant_id:
            query = query.where(IntakeItem.tenant_id == tenant_id)
        if review_queue:
            query = query.where(IntakeItem.needs_review.is_(True))
        return db.scalars(query).all()

    scoped_tenant_id = resolve_tenant_scope(context, tenant_id)
    query = query.where(IntakeItem.tenant_id == scoped_tenant_id)
    if review_queue:
        query = query.where(IntakeItem.needs_review.is_(True))
    return db.scalars(query).all()


@router.get(
    "/items/{item_id}",
    response_model=IntakeItemResponse,
    operation_id="intake_items_get",
    summary="Get intake item",
)
def get_intake_item(
    item_id: str,
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    item = _ensure_item_access(db.get(IntakeItem, item_id), context)
    return item


@router.post(
    "/upload",
    response_model=IntakeItemResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="intake_upload",
    summary="Upload intake file",
)
async def upload_intake_files(
    file: UploadFile = File(...),
    context: RequestContext = Depends(require_permissions("intake_write")),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    tenant_id = _tenant_id_from_context(context)
    payload = await file.read()
    original_filename = file.filename or "upload.bin"
    created_at = datetime.utcnow()

    batch = IngestionBatch(
        tenant_id=tenant_id,
        source_channel="upload",
        status=IngestionBatchStatus.PROCESSING,
        total_documents=1,
        created_documents=0,
        matched_documents=0,
        needs_review_documents=0,
        duplicate_documents=0,
        blocked_documents=0,
        error_documents=0,
        summary_json="{}",
        created_by=context.user.id,
        started_at=created_at,
    )
    db.add(batch)
    db.flush()

    processed = process_intake_upload(
        tenant_id=tenant_id,
        original_filename=original_filename,
        mime_type=file.content_type or "application/octet-stream",
        payload=payload,
    )

    duplicate_of_item_id: str | None = db.scalars(
        select(IntakeItem.id)
        .where(IntakeItem.tenant_id == tenant_id)
        .where(IntakeItem.content_hash == processed.content_hash)
        .limit(1)
    ).first()

    is_duplicate = duplicate_of_item_id is not None
    if is_duplicate:
        processed.needs_review = True
        processed.review_reason = f"Possible duplicate of intake item {duplicate_of_item_id}."
        processed.status = IntakeStatus.REVIEWING
        processed.processing_stage = "reviewing"

    item = IntakeItem(
        tenant_id=tenant_id,
        batch_id=batch.id,
        project_id=None,
        filename=processed.filename,
        original_filename=processed.original_filename,
        file_path=processed.file_path,
        mime_type=processed.mime_type,
        file_size_bytes=processed.file_size_bytes,
        content_hash=processed.content_hash,
        document_type=processed.document_type,
        source="manual",
        status=processed.status,
        processing_stage=processed.processing_stage,
        extracted_summary=processed.extracted_summary,
        extracted_text=processed.extracted_text,
        ai_summary="",
        extracted_entities=processed.extracted_entities,
        ocr_status=processed.ocr_status,
        ai_status=processed.ai_status,
        needs_review=processed.needs_review,
        review_reason=processed.review_reason,
        duplicate_of_item_id=duplicate_of_item_id,
        classification_confidence=processed.classification_confidence,
        match_confidence=processed.match_confidence,
        conflict_notes="",
        created_by=context.user.id,
    )

    db.add(item)
    db.flush()

    created_ticket_ids: list[str] = []
    extracted_entities = json.loads(processed.extracted_entities or "{}")
    ticket_number = (extracted_entities.get("ticket_number") or "").strip()
    if _should_auto_create_ticket(
        item,
        ticket_number=ticket_number,
        is_duplicate=is_duplicate,
        extracted_entities=extracted_entities,
    ):
        ticket = Ticket(
            tenant_id=tenant_id,
            intake_item_id=item.id,
            project_id=None,
            ticket_number=ticket_number,
            truck=(extracted_entities.get("truck") or "").strip(),
            driver=(extracted_entities.get("driver") or "").strip(),
            material=(extracted_entities.get("material") or "").strip(),
            origin="",
            destination="",
            status="draft",
            notes="Auto-created from intake extraction baseline.",
            created_by=context.user.id,
        )
        db.add(ticket)
        db.flush()
        created_ticket_ids.append(ticket.id)

    batch.created_documents = 1
    batch.matched_documents = len(created_ticket_ids)
    batch.duplicate_documents = 1 if is_duplicate else 0
    batch.needs_review_documents = 1 if processed.needs_review else 0
    batch.status = (
        IngestionBatchStatus.COMPLETED_WITH_REVIEW
        if processed.needs_review
        else IngestionBatchStatus.COMPLETED
    )
    batch.completed_at = datetime.utcnow()
    batch.summary_json = json.dumps(
        {
            "created_item_ids": [item.id],
            "created_ticket_ids": created_ticket_ids,
            "needs_review": processed.needs_review,
        }
    )

    _add_integration_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=context.user.id,
        event_type="intake_item_uploaded",
        resource_id=item.id,
        payload={
            "batch_id": batch.id,
            "status": item.status.value,
            "needs_review": item.needs_review,
            "duplicate_of_item_id": item.duplicate_of_item_id,
            "created_ticket_count": len(created_ticket_ids),
        },
    )

    db.commit()
    db.refresh(item)

    # Auto-trigger OCR extraction as a background task after successful upload.
    # Skipped for duplicates (already extracted from the original).
    if processed.extracted_text and not is_duplicate:
        background_tasks.add_task(
            _run_extraction_background,
            item_id=item.id,
            tenant_id=tenant_id,
            user_id=context.user.id,
        )

    return item


@router.post(
    "/placement/suggest",
    response_model=IntakePlacementSuggestionListResponse,
    operation_id="intake_placement_suggest",
    summary="Suggest destination placement for intake items",
)
def suggest_intake_item_placements(
    payload: IntakePlacementSuggestionRequest,
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    requested_ids = [item_id.strip() for item_id in payload.item_ids if item_id.strip()]
    if not requested_ids:
        return IntakePlacementSuggestionListResponse(items=[])

    scoped_items = db.scalars(
        select(IntakeItem)
        .where(IntakeItem.tenant_id == tenant_id)
        .where(IntakeItem.id.in_(requested_ids))
    ).all()
    item_by_id = {item.id: item for item in scoped_items}

    suggestion_items: list[IntakePlacementSuggestionResponse] = []
    for item_id in requested_ids:
        item = item_by_id.get(item_id)
        if not item:
            continue

        suggestion = suggest_intake_placement(item)
        suggestion_items.append(
            IntakePlacementSuggestionResponse(
                item_id=item.id,
                destination_key=suggestion.destination_key,
                destination_label=suggestion.destination_label,
                destination_href=suggestion.destination_href,
                confidence=suggestion.confidence,
                reason=suggestion.reason,
                signal_source=suggestion.signal_source,
            )
        )
        _add_intake_audit_log(
            db,
            item=item,
            actor_user_id=context.user.id,
            action="ai_suggest_intake_placement",
            details=(
                f"destination={suggestion.destination_key};"
                f"confidence={suggestion.confidence:.2f};"
                f"signal_source={suggestion.signal_source}"
            ),
        )

    db.commit()
    return IntakePlacementSuggestionListResponse(items=suggestion_items)


@router.post(
    "/conflicts/suggest",
    response_model=IntakeConflictSuggestionListResponse,
    operation_id="intake_conflicts_suggest",
    summary="Suggest intake data conflicts using document precedence",
)
def suggest_intake_conflicts(
    payload: IntakePlacementSuggestionRequest,
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    requested_ids = [item_id.strip() for item_id in payload.item_ids if item_id.strip()]
    if not requested_ids:
        return IntakeConflictSuggestionListResponse(items=[])

    scoped_items = db.scalars(
        select(IntakeItem)
        .where(IntakeItem.tenant_id == tenant_id)
        .where(IntakeItem.id.in_(requested_ids))
        .order_by(IntakeItem.created_at.asc())
    ).all()

    suggestions = build_quantity_conflict_suggestions(scoped_items)
    response_items: list[IntakeConflictSuggestionResponse] = []

    for suggestion in suggestions:
        candidates = [
            IntakeConflictValueCandidateResponse(
                item_id=candidate.item_id,
                field_name=candidate.field_name,
                value=candidate.value,
                unit=candidate.unit,
                document_type=candidate.document_type,
                document_subtype=candidate.document_subtype,
                source_text=candidate.source_text,
                page=candidate.page,
                confidence=candidate.confidence,
                created_at=candidate.created_at,
            )
            for candidate in suggestion.candidates
        ]

        recommended = IntakeConflictValueCandidateResponse(
            item_id=suggestion.recommended.item_id,
            field_name=suggestion.recommended.field_name,
            value=suggestion.recommended.value,
            unit=suggestion.recommended.unit,
            document_type=suggestion.recommended.document_type,
            document_subtype=suggestion.recommended.document_subtype,
            source_text=suggestion.recommended.source_text,
            page=suggestion.recommended.page,
            confidence=suggestion.recommended.confidence,
            created_at=suggestion.recommended.created_at,
        )

        response_items.append(
            IntakeConflictSuggestionResponse(
                field_name=suggestion.field_name,
                candidates=candidates,
                recommended=recommended,
                reason=suggestion.reason,
            )
        )

    return IntakeConflictSuggestionListResponse(items=response_items)


@router.post(
    "/conflicts/resolve",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="intake_conflicts_resolve",
    summary="Record user decision for intake conflict resolution",
)
def resolve_intake_conflict(
    payload: IntakeConflictResolveRequest,
    context: RequestContext = Depends(require_permissions("intake_review")),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id_from_context(context)
    selected_item = db.scalars(
        select(IntakeItem)
        .where(IntakeItem.id == payload.selected_item_id)
        .where(IntakeItem.tenant_id == tenant_id)
    ).first()
    if not selected_item:
        raise HTTPException(status_code=404, detail="Selected intake item not found")

    _add_intake_audit_log(
        db,
        item=selected_item,
        actor_user_id=context.user.id,
        action="resolve_intake_conflict",
        details=(
            f"field={payload.field_name};"
            f"selected_value={payload.selected_value};"
            f"rationale={payload.rationale or 'none'}"
        ),
    )
    _add_integration_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=context.user.id,
        event_type="intake_conflict_resolved",
        resource_id=selected_item.id,
        payload={
            "field_name": payload.field_name,
            "selected_item_id": payload.selected_item_id,
            "selected_value": payload.selected_value,
            "rationale": payload.rationale,
        },
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/items/{item_id}/file",
    operation_id="intake_get_file",
    summary="Download intake item file",
)
def get_intake_file(
    item_id: str,
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    """Serve the uploaded file for an intake item with tenant isolation."""
    tenant_id = _tenant_id_from_context(context)

    # Load the intake item with tenant isolation
    item = db.scalars(
        select(IntakeItem)
        .where(IntakeItem.id == item_id)
        .where(IntakeItem.tenant_id == tenant_id)
    ).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake item not found",
        )

    # Construct the file path from the stored file_path
    # file_path is relative to repo root, e.g., "backend/storage/intake/tenant_id/2026/07/27/uuid_filename"
    try:
        # Get repo root (same as in intake_processing.py)
        repo_root = Path(__file__).resolve().parents[4]
        file_path = repo_root / item.file_path
        
        # Verify the file exists
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk",
            )
        
        # Verify the file is within the intake storage directory (security check)
        intake_root = repo_root / "backend" / "storage" / "intake" / tenant_id
        if not file_path.is_relative_to(intake_root):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        # Return the file with the original filename and MIME type
        return FileResponse(
            path=file_path,
            media_type=item.mime_type,
            filename=item.original_filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving file: {str(e)}",
        )


@router.post(
    "/items/{item_id}/approve",
    response_model=IntakeItemResponse,
    operation_id="intake_items_approve",
    summary="Approve intake item",
)
def approve_intake_item(
    item_id: str,
    context: RequestContext = Depends(require_permissions("intake_review")),
    db: Session = Depends(get_db),
):
    item = _ensure_item_access(db.get(IntakeItem, item_id), context)

    item.status = IntakeStatus.APPROVED
    item.needs_review = False
    item.reviewed_by = context.user.id
    item.reviewed_at = datetime.utcnow()

    _add_intake_audit_log(
        db,
        item=item,
        actor_user_id=context.user.id,
        action="approve_intake_item",
        details="Intake item approved through review workflow.",
    )
    _add_integration_event(
        db,
        tenant_id=item.tenant_id,
        actor_user_id=context.user.id,
        event_type="intake_item_approved",
        resource_id=item.id,
        payload={
            "status": item.status.value,
            "needs_review": item.needs_review,
        },
    )

    db.commit()
    db.refresh(item)
    return item


@router.post(
    "/items/{item_id}/reject",
    response_model=IntakeItemResponse,
    operation_id="intake_items_reject",
    summary="Reject intake item",
)
def reject_intake_item(
    item_id: str,
    reason: str | None = None,
    context: RequestContext = Depends(require_permissions("intake_review")),
    db: Session = Depends(get_db),
):
    item = _ensure_item_access(db.get(IntakeItem, item_id), context)

    item.status = IntakeStatus.REJECTED
    item.needs_review = True
    item.review_reason = reason or "Rejected by reviewer"
    item.reviewed_by = context.user.id
    item.reviewed_at = datetime.utcnow()

    _add_intake_audit_log(
        db,
        item=item,
        actor_user_id=context.user.id,
        action="reject_intake_item",
        details=f"Intake item rejected. reason={item.review_reason}",
    )
    _add_integration_event(
        db,
        tenant_id=item.tenant_id,
        actor_user_id=context.user.id,
        event_type="intake_item_rejected",
        resource_id=item.id,
        payload={
            "status": item.status.value,
            "needs_review": item.needs_review,
            "review_reason": item.review_reason,
        },
    )

    db.commit()
    db.refresh(item)
    return item


@router.post(
    "/items/{item_id}/resolve-duplicate",
    response_model=IntakeItemResponse,
    operation_id="intake_items_resolve_duplicate",
    summary="Resolve duplicate intake item",
)
def resolve_duplicate_intake_item(
    item_id: str,
    payload: IntakeDuplicateResolutionRequest,
    context: RequestContext = Depends(require_permissions("intake_review")),
    db: Session = Depends(get_db),
):
    item = _ensure_item_access(db.get(IntakeItem, item_id), context)
    previous_duplicate_of = item.duplicate_of_item_id

    resolved_duplicate_of = payload.duplicate_of_item_id or item.duplicate_of_item_id
    if not resolved_duplicate_of:
        raise HTTPException(status_code=400, detail="Item is not marked as a duplicate")
    if resolved_duplicate_of == item.id:
        raise HTTPException(status_code=400, detail="Item cannot be marked duplicate of itself")

    duplicate_target = db.get(IntakeItem, resolved_duplicate_of)
    if not duplicate_target or duplicate_target.tenant_id != item.tenant_id:
        raise HTTPException(status_code=400, detail="Duplicate target item is invalid")

    item.duplicate_of_item_id = resolved_duplicate_of
    item.status = IntakeStatus.APPROVED
    item.needs_review = False
    item.review_reason = "Duplicate resolved by reviewer"
    item.reviewed_by = context.user.id
    item.reviewed_at = datetime.utcnow()
    if payload.conflict_notes:
        item.conflict_notes = payload.conflict_notes.strip()

    _add_intake_audit_log(
        db,
        item=item,
        actor_user_id=context.user.id,
        action="resolve_intake_duplicate",
        details=(
            f"resolved_duplicate_of={resolved_duplicate_of}; "
            f"previous_duplicate_of={previous_duplicate_of or ''}; "
            f"notes={item.conflict_notes or ''}"
        ),
    )
    _add_integration_event(
        db,
        tenant_id=item.tenant_id,
        actor_user_id=context.user.id,
        event_type="intake_item_duplicate_resolved",
        resource_id=item.id,
        payload={
            "status": item.status.value,
            "needs_review": item.needs_review,
            "duplicate_of_item_id": item.duplicate_of_item_id,
        },
    )

    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/events",
    response_model=list[IntakeIntegrationEventResponse],
    operation_id="intake_events_list",
    summary="List intake integration events",
)
def list_intake_integration_events(
    tenant_id: str | None = Query(default=None),
    event_status: str | None = Query(default="pending", alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    query = select(IntegrationEvent).order_by(IntegrationEvent.created_at.asc()).limit(limit)

    if "*" in context.permissions:
        if tenant_id:
            query = query.where(IntegrationEvent.tenant_id == tenant_id)
    else:
        scoped_tenant_id = resolve_tenant_scope(context, tenant_id)
        query = query.where(IntegrationEvent.tenant_id == scoped_tenant_id)

    if event_status:
        query = query.where(IntegrationEvent.status == event_status)

    return db.scalars(query).all()


@router.post(
    "/events/{event_id}/mark-processed",
    response_model=IntakeIntegrationEventResponse,
    operation_id="intake_events_mark_processed",
    summary="Mark intake integration event as processed",
)
def mark_intake_integration_event_processed(
    event_id: str,
    payload: IntakeIntegrationEventProcessRequest,
    context: RequestContext = Depends(require_permissions("intake_review")),
    db: Session = Depends(get_db),
):
    event = _ensure_event_access(db.get(IntegrationEvent, event_id), context)

    event_payload = json.loads(event.payload_json or "{}")
    event_payload["processed_by"] = context.user.id
    event_payload["processing_notes"] = payload.processing_notes.strip()
    if payload.status == "failed":
        failure_reason = payload.failure_reason.strip()
        if not failure_reason:
            raise HTTPException(status_code=400, detail="failure_reason is required when status=failed")
        event_payload["failure_reason"] = failure_reason
    else:
        event_payload.pop("failure_reason", None)

    event.status = payload.status
    event.payload_json = json.dumps(event_payload)
    event.processed_at = datetime.utcnow()

    db.commit()
    db.refresh(event)
    return event


@router.post(
    "/events/{event_id}/retry",
    response_model=IntakeIntegrationEventResponse,
    operation_id="intake_events_retry",
    summary="Retry failed intake integration event",
)
def retry_intake_integration_event(
    event_id: str,
    payload: IntakeIntegrationEventRetryRequest,
    context: RequestContext = Depends(require_permissions("intake_review")),
    db: Session = Depends(get_db),
):
    event = _ensure_event_access(db.get(IntegrationEvent, event_id), context)
    if event.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed events can be retried")

    event_payload = json.loads(event.payload_json or "{}")
    next_retry_count = int(event_payload.get("retry_count") or 0) + 1
    event_payload["retry_count"] = next_retry_count

    if next_retry_count > MAX_INTEGRATION_EVENT_RETRIES:
        event.status = "dead_lettered"
        event_payload["dead_letter_reason"] = (
            f"Exceeded max retries ({MAX_INTEGRATION_EVENT_RETRIES})"
        )
        event_payload["dead_lettered_by"] = context.user.id
        event_payload["dead_lettered_at"] = datetime.utcnow().isoformat()
        event.processed_at = datetime.utcnow()
    else:
        event_payload["last_retry_by"] = context.user.id
        event_payload["last_retry_notes"] = payload.retry_notes.strip()
        event_payload.pop("failure_reason", None)
        event.status = "pending"
        event.processed_at = None

    event.payload_json = json.dumps(event_payload)

    db.commit()
    db.refresh(event)
    return event


@router.post(
    "/events/{event_id}/replay-dead-letter",
    response_model=IntakeIntegrationEventResponse,
    operation_id="intake_events_replay_dead_letter",
    summary="Replay dead-lettered intake integration event",
)
def replay_dead_letter_intake_integration_event(
    event_id: str,
    payload: IntakeIntegrationEventReplayRequest,
    context: RequestContext = Depends(require_permissions("intake_review")),
    db: Session = Depends(get_db),
):
    event = _ensure_event_access(db.get(IntegrationEvent, event_id), context)
    if event.status != "dead_lettered":
        raise HTTPException(status_code=400, detail="Only dead-lettered events can be replayed")

    approval_notes = payload.approval_notes.strip()
    if not approval_notes:
        raise HTTPException(status_code=400, detail="approval_notes is required")

    event_payload = json.loads(event.payload_json or "{}")
    replay_count = int(event_payload.get("replay_count") or 0) + 1
    event_payload["replay_count"] = replay_count
    event_payload["replay_approved_by"] = context.user.id
    event_payload["replay_approval_notes"] = approval_notes
    event_payload["replay_approved_at"] = datetime.utcnow().isoformat()
    event_payload.pop("dead_letter_reason", None)
    event_payload.pop("dead_lettered_by", None)
    event_payload.pop("dead_lettered_at", None)
    event_payload.pop("failure_reason", None)

    event.status = "pending"
    event.payload_json = json.dumps(event_payload)
    event.processed_at = None

    db.add(
        AuditLog(
            tenant_id=event.tenant_id,
            actor_user_id=context.user.id,
            action="replay_dead_letter_intake_event",
            resource_type="integration_event",
            resource_id=event.id,
            details=(
                "Manual dead-letter replay approved. "
                f"replay_count={replay_count}; approval_notes={approval_notes}"
            ),
            created_by=context.user.id,
        )
    )

    db.commit()
    db.refresh(event)
    return event


def _build_replay_audit_history_query(
    *,
    context: RequestContext,
    tenant_id: str | None,
    event_id: str | None,
    start_created_at: datetime | None,
    end_created_at: datetime | None,
    cursor_created_at: datetime | None,
    limit: int,
):
    _validate_replay_audit_history_date_range(
        start_created_at=start_created_at,
        end_created_at=end_created_at,
    )

    query = (
        select(AuditLog)
        .where(AuditLog.action == "replay_dead_letter_intake_event")
        .where(AuditLog.resource_type == "integration_event")
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )

    if tenant_id is not None or "*" not in context.permissions:
        scoped_tenant_id = resolve_tenant_scope(
            context,
            tenant_id,
            cross_tenant_detail="Cannot read replay history for another tenant",
        )
        query = query.where(AuditLog.tenant_id == scoped_tenant_id)

    if event_id:
        query = query.where(AuditLog.resource_id == event_id)

    if start_created_at:
        query = query.where(AuditLog.created_at >= start_created_at)

    if end_created_at:
        query = query.where(AuditLog.created_at <= end_created_at)

    if cursor_created_at:
        query = query.where(AuditLog.created_at < cursor_created_at)

    return query


def _validate_replay_audit_history_date_range(
    *,
    start_created_at: datetime | None,
    end_created_at: datetime | None,
) -> None:
    if start_created_at and end_created_at and _as_utc(start_created_at) > _as_utc(end_created_at):
        raise HTTPException(status_code=400, detail="start_created_at must be <= end_created_at")


def _resolve_replay_export_tenant_scope(
    *,
    context: RequestContext,
    requested_tenant_id: str | None,
    required_purpose: str = "replay export token generation",
) -> str:
    return resolve_tenant_scope(
        context,
        requested_tenant_id,
        require_explicit_for_super_admin=True,
        missing_tenant_detail=f"tenant_id is required for {required_purpose}",
        cross_tenant_detail="Cannot export replay history for another tenant",
    )


def _parse_export_token_datetime(
    *,
    value: str | None,
    field_name: str,
) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} in export token") from exc


def _render_replay_audit_history_export_response(
    *,
    context: RequestContext,
    db: Session,
    tenant_id: str | None,
    event_id: str | None,
    start_created_at: datetime | None,
    end_created_at: datetime | None,
    cursor_created_at: datetime | None,
    output: str,
    limit: int,
):
    query = _build_replay_audit_history_query(
        context=context,
        tenant_id=tenant_id,
        event_id=event_id,
        start_created_at=start_created_at,
        end_created_at=end_created_at,
        cursor_created_at=cursor_created_at,
        limit=limit + 1,
    )
    entries = db.scalars(query).all()
    has_more = len(entries) > limit
    if has_more:
        entries = entries[:limit]

    payload = [
        IntakeReplayAuditEntryResponse.model_validate(entry).model_dump(mode="json")
        for entry in entries
    ]

    generated_at_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename_extension = "json" if output == "json" else "csv"
    export_filename = f"intake-replay-history-{generated_at_stamp}.{filename_extension}"

    headers: dict[str, str] = {}
    if has_more and entries:
        headers["X-Next-Cursor-Created-At"] = entries[-1].created_at.isoformat()
    headers["Content-Disposition"] = f'attachment; filename="{export_filename}"'

    if output == "json":
        return JSONResponse(payload, headers=headers)

    fieldnames = [
        "id",
        "tenant_id",
        "action",
        "resource_type",
        "resource_id",
        "details",
        "actor_user_id",
        "created_by",
        "created_at",
        "updated_at",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(payload)

    return PlainTextResponse(buffer.getvalue(), media_type="text/csv", headers=headers)


def _build_replay_export_token_audit_query(
    *,
    context: RequestContext,
    tenant_id: str | None,
    token_id: str | None,
    actor_user_id: str | None,
    action: str | None,
    start_created_at: datetime | None,
    end_created_at: datetime | None,
    cursor_created_at: datetime | None,
    cursor_id: UUID | None,
    sort_desc: bool,
    limit: int,
):
    _validate_replay_audit_history_date_range(
        start_created_at=start_created_at,
        end_created_at=end_created_at,
    )

    if cursor_id is not None and cursor_created_at is None:
        raise HTTPException(
            status_code=400,
            detail="cursor_id requires cursor_created_at",
        )

    query = (
        select(AuditLog)
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.action.in_(REPLAY_EXPORT_TOKEN_AUDIT_ACTIONS))
        .limit(limit)
    )

    if sort_desc:
        query = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    else:
        query = query.order_by(AuditLog.created_at.asc(), AuditLog.id.asc())

    if tenant_id is not None or "*" not in context.permissions:
        scoped_tenant_id = resolve_tenant_scope(
            context,
            tenant_id,
            cross_tenant_detail="Cannot read replay export token history for another tenant",
        )
        query = query.where(AuditLog.tenant_id == scoped_tenant_id)

    if token_id:
        query = query.where(AuditLog.resource_id == token_id)

    if actor_user_id:
        query = query.where(AuditLog.actor_user_id == actor_user_id)

    if action:
        query = query.where(AuditLog.action == action)

    if start_created_at:
        query = query.where(AuditLog.created_at >= start_created_at)

    if end_created_at:
        query = query.where(AuditLog.created_at <= end_created_at)

    if cursor_created_at:
        if cursor_id:
            cursor_id_text = str(cursor_id)
            if sort_desc:
                query = query.where(
                    or_(
                        AuditLog.created_at < cursor_created_at,
                        and_(
                            AuditLog.created_at == cursor_created_at,
                            AuditLog.id < cursor_id_text,
                        ),
                    )
                )
            else:
                query = query.where(
                    or_(
                        AuditLog.created_at > cursor_created_at,
                        and_(
                            AuditLog.created_at == cursor_created_at,
                            AuditLog.id > cursor_id_text,
                        ),
                    )
                )
        else:
            if sort_desc:
                query = query.where(AuditLog.created_at < cursor_created_at)
            else:
                query = query.where(AuditLog.created_at > cursor_created_at)

    return query


def _build_replay_export_token_audit_summary_query(
    *,
    context: RequestContext,
    tenant_id: str | None,
    token_id: str | None,
    actor_user_id: str | None,
    action: str | None,
    start_created_at: datetime | None,
    end_created_at: datetime | None,
):
    _validate_replay_audit_history_date_range(
        start_created_at=start_created_at,
        end_created_at=end_created_at,
    )

    query = select(
        func.count(AuditLog.id).label("total_entries"),
        func.sum(case((AuditLog.action == "issue_replay_history_export_token", 1), else_=0)).label("issued_count"),
        func.sum(case((AuditLog.action == "consume_replay_history_export_token", 1), else_=0)).label("consumed_count"),
        func.sum(case((AuditLog.action == "revoke_replay_history_export_token", 1), else_=0)).label("revoked_count"),
        func.count(func.distinct(AuditLog.actor_user_id)).label("unique_actor_count"),
        func.max(AuditLog.created_at).label("latest_created_at"),
    ).where(
        AuditLog.resource_type == "replay_history_export_token",
        AuditLog.action.in_(REPLAY_EXPORT_TOKEN_AUDIT_ACTIONS),
    )

    if tenant_id is not None or "*" not in context.permissions:
        scoped_tenant_id = resolve_tenant_scope(
            context,
            tenant_id,
            cross_tenant_detail="Cannot read replay export token summary for another tenant",
        )
        query = query.where(AuditLog.tenant_id == scoped_tenant_id)

    if token_id:
        query = query.where(AuditLog.resource_id == token_id)

    if actor_user_id:
        query = query.where(AuditLog.actor_user_id == actor_user_id)

    if action:
        query = query.where(AuditLog.action == action)

    if start_created_at:
        query = query.where(AuditLog.created_at >= start_created_at)

    if end_created_at:
        query = query.where(AuditLog.created_at <= end_created_at)

    return query


def _bucket_replay_export_token_audit_trend(
    *,
    logs: list[AuditLog],
    granularity: str,
) -> list[IntakeReplayExportTokenAuditTrendBucketResponse]:
    buckets: dict[datetime, dict[str, int]] = {}
    for log in logs:
        created_at = _as_utc(log.created_at)
        if granularity == "hour":
            bucket_start = created_at.replace(minute=0, second=0, microsecond=0)
        else:
            bucket_start = created_at.replace(hour=0, minute=0, second=0, microsecond=0)

        bucket = buckets.setdefault(
            bucket_start,
            {"issued_count": 0, "consumed_count": 0, "revoked_count": 0, "total_count": 0},
        )
        if log.action == "issue_replay_history_export_token":
            bucket["issued_count"] += 1
        elif log.action == "consume_replay_history_export_token":
            bucket["consumed_count"] += 1
        elif log.action == "revoke_replay_history_export_token":
            bucket["revoked_count"] += 1
        bucket["total_count"] += 1

    return [
        IntakeReplayExportTokenAuditTrendBucketResponse(
            bucket_start_created_at=bucket_start,
            issued_count=counts["issued_count"],
            consumed_count=counts["consumed_count"],
            revoked_count=counts["revoked_count"],
            total_count=counts["total_count"],
        )
        for bucket_start, counts in sorted(buckets.items(), key=lambda item: item[0])
    ]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_token_issue_details(details: str) -> tuple[str | None, str | None, int | None]:
    match = _TOKEN_ISSUE_DETAILS_PATTERN.search(details)
    if not match:
        return None, None, None

    event_id, output, limit_str = match.groups()
    export_limit: int | None
    try:
        export_limit = int(limit_str)
    except ValueError:
        export_limit = None

    normalized_event_id = None if event_id == "all" else event_id
    return normalized_event_id, output, export_limit


def _validate_replay_export_token_state_cursor(
    *,
    cursor_issued_at: datetime | None,
    cursor_token_id: UUID | None,
) -> None:
    if cursor_token_id is not None and cursor_issued_at is None:
        raise HTTPException(
            status_code=400,
            detail="cursor_token_id requires cursor_issued_at",
        )


def _build_replay_export_token_issue_query(
    *,
    context: RequestContext,
    tenant_id: str | None,
    token_id: str | None,
    actor_user_id: str | None,
    start_issued_at: datetime | None,
    end_issued_at: datetime | None,
    cursor_issued_at: datetime | None,
    cursor_token_id: UUID | None,
    sort_desc: bool,
    limit: int | None,
):
    _validate_replay_audit_history_date_range(
        start_created_at=start_issued_at,
        end_created_at=end_issued_at,
    )
    _validate_replay_export_token_state_cursor(
        cursor_issued_at=cursor_issued_at,
        cursor_token_id=cursor_token_id,
    )

    query = (
        select(AuditLog)
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.action == "issue_replay_history_export_token")
    )

    if tenant_id is not None or "*" not in context.permissions:
        scoped_tenant_id = resolve_tenant_scope(
            context,
            tenant_id,
            cross_tenant_detail="Cannot read replay export token states for another tenant",
        )
        query = query.where(AuditLog.tenant_id == scoped_tenant_id)

    if token_id:
        query = query.where(AuditLog.resource_id == token_id)

    if actor_user_id:
        query = query.where(AuditLog.actor_user_id == actor_user_id)

    if start_issued_at:
        query = query.where(AuditLog.created_at >= start_issued_at)

    if end_issued_at:
        query = query.where(AuditLog.created_at <= end_issued_at)

    if cursor_issued_at:
        if cursor_token_id:
            cursor_token_id_text = str(cursor_token_id)
            if sort_desc:
                query = query.where(
                    or_(
                        AuditLog.created_at < cursor_issued_at,
                        and_(
                            AuditLog.created_at == cursor_issued_at,
                            AuditLog.resource_id < cursor_token_id_text,
                        ),
                    )
                )
            else:
                query = query.where(
                    or_(
                        AuditLog.created_at > cursor_issued_at,
                        and_(
                            AuditLog.created_at == cursor_issued_at,
                            AuditLog.resource_id > cursor_token_id_text,
                        ),
                    )
                )
        elif sort_desc:
            query = query.where(AuditLog.created_at < cursor_issued_at)
        else:
            query = query.where(AuditLog.created_at > cursor_issued_at)

    if sort_desc:
        query = query.order_by(AuditLog.created_at.desc(), AuditLog.resource_id.desc())
    else:
        query = query.order_by(AuditLog.created_at.asc(), AuditLog.resource_id.asc())

    if limit is not None:
        query = query.limit(limit)

    return query


def _project_replay_export_token_states(
    *,
    db: Session,
    issue_logs: list[AuditLog],
) -> list[IntakeReplayExportTokenStateResponse]:
    if not issue_logs:
        return []

    issue_by_token_id = {log.resource_id: log for log in issue_logs}
    token_ids = list(issue_by_token_id.keys())

    lifecycle_logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.resource_id.in_(token_ids))
        .where(
            AuditLog.action.in_(
                (
                    "consume_replay_history_export_token",
                    "revoke_replay_history_export_token",
                )
            )
        )
        .order_by(AuditLog.created_at.desc())
    ).all()

    consume_by_token_id: dict[str, AuditLog] = {}
    revoke_by_token_id: dict[str, AuditLog] = {}
    for log in lifecycle_logs:
        if log.action == "consume_replay_history_export_token" and log.resource_id not in consume_by_token_id:
            consume_by_token_id[log.resource_id] = log
        if log.action == "revoke_replay_history_export_token" and log.resource_id not in revoke_by_token_id:
            revoke_by_token_id[log.resource_id] = log

    now_utc = datetime.now(timezone.utc)
    states: list[IntakeReplayExportTokenStateResponse] = []
    for issue in issue_logs:
        consumed = consume_by_token_id.get(issue.resource_id)
        revoked = revoke_by_token_id.get(issue.resource_id)

        issued_at_utc = _as_utc(issue.created_at)
        expires_at = issued_at_utc + timedelta(minutes=settings.INTAKE_REPLAY_EXPORT_TOKEN_MINUTES)

        state = "issued"
        if revoked is not None:
            state = "revoked"
        elif consumed is not None:
            state = "consumed"
        elif expires_at < now_utc:
            state = "expired"

        latest_activity = issued_at_utc
        if consumed is not None:
            latest_activity = max(latest_activity, _as_utc(consumed.created_at))
        if revoked is not None:
            latest_activity = max(latest_activity, _as_utc(revoked.created_at))

        event_id, output, export_limit = _parse_token_issue_details(issue.details)
        states.append(
            IntakeReplayExportTokenStateResponse(
                token_id=issue.resource_id,
                tenant_id=issue.tenant_id,
                state=state,
                issued_at=issued_at_utc,
                issued_by_user_id=issue.actor_user_id,
                consumed_at=_as_utc(consumed.created_at) if consumed else None,
                consumed_by_user_id=consumed.actor_user_id if consumed else None,
                revoked_at=_as_utc(revoked.created_at) if revoked else None,
                revoked_by_user_id=revoked.actor_user_id if revoked else None,
                expires_at=expires_at,
                latest_activity_at=latest_activity,
                event_id=event_id,
                output=output,
                export_limit=export_limit,
            )
        )

    return states


@router.get(
    "/events/replay-history",
    response_model=list[IntakeReplayAuditEntryResponse],
    operation_id="intake_events_replay_history",
    summary="List dead-letter replay audit history",
)
def list_replay_dead_letter_audit_history(
    response: Response,
    tenant_id: str | None = Query(default=None),
    event_id: str | None = Query(default=None),
    start_created_at: datetime | None = Query(default=None),
    end_created_at: datetime | None = Query(default=None),
    cursor_created_at: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    query = _build_replay_audit_history_query(
        context=context,
        tenant_id=tenant_id,
        event_id=event_id,
        start_created_at=start_created_at,
        end_created_at=end_created_at,
        cursor_created_at=cursor_created_at,
        limit=limit + 1,
    )
    entries = db.scalars(query).all()
    has_more = len(entries) > limit
    if has_more:
        entries = entries[:limit]
        response.headers["X-Next-Cursor-Created-At"] = entries[-1].created_at.isoformat()

    return entries


@router.get(
    "/events/replay-history/export-token-history",
    response_model=list[IntakeReplayExportTokenAuditEntryResponse],
    operation_id="intake_events_replay_history_export_token_history",
    summary="List replay export token audit history",
)
def list_replay_export_token_audit_history(
    response: Response,
    tenant_id: str | None = Query(default=None),
    token_id: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    action: str | None = Query(
        default=None,
        pattern="^(issue_replay_history_export_token|consume_replay_history_export_token|revoke_replay_history_export_token)$",
    ),
    start_created_at: datetime | None = Query(default=None),
    end_created_at: datetime | None = Query(default=None),
    cursor_created_at: datetime | None = Query(default=None),
    cursor_id: UUID | None = Query(default=None),
    sort: str = Query(default="-created_at", pattern=r"^(-created_at|\+created_at)$"),
    limit: int = Query(default=100, ge=1, le=500),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    effective_limit = min(limit, REPLAY_EXPORT_TOKEN_AUDIT_LIMIT_CAP)
    sort_desc = sort == "-created_at"
    query = _build_replay_export_token_audit_query(
        context=context,
        tenant_id=tenant_id,
        token_id=token_id,
        actor_user_id=actor_user_id,
        action=action,
        start_created_at=start_created_at,
        end_created_at=end_created_at,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
        sort_desc=sort_desc,
        limit=effective_limit + 1,
    )
    entries = db.scalars(query).all()
    has_more = len(entries) > effective_limit
    if has_more:
        entries = entries[:effective_limit]
        response.headers["X-Next-Cursor-Created-At"] = entries[-1].created_at.isoformat()
        response.headers["X-Next-Cursor-Id"] = entries[-1].id

    return entries


@router.get(
    "/events/replay-history/export-token-history/list",
    response_model=IntakeReplayExportTokenAuditHistoryListResponse,
    operation_id="intake_events_replay_history_export_token_history_list",
    summary="List replay export token audit history with envelope metadata",
)
def list_replay_export_token_audit_history_with_envelope(
    tenant_id: str | None = Query(default=None),
    token_id: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    action: str | None = Query(
        default=None,
        pattern="^(issue_replay_history_export_token|consume_replay_history_export_token|revoke_replay_history_export_token)$",
    ),
    start_created_at: datetime | None = Query(default=None),
    end_created_at: datetime | None = Query(default=None),
    cursor_created_at: datetime | None = Query(default=None),
    cursor_id: UUID | None = Query(default=None),
    sort: str = Query(default="-created_at", pattern=r"^(-created_at|\+created_at)$"),
    limit: int = Query(default=100, ge=1, le=500),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    effective_limit = min(limit, REPLAY_EXPORT_TOKEN_AUDIT_LIMIT_CAP)
    sort_desc = sort == "-created_at"
    query = _build_replay_export_token_audit_query(
        context=context,
        tenant_id=tenant_id,
        token_id=token_id,
        actor_user_id=actor_user_id,
        action=action,
        start_created_at=start_created_at,
        end_created_at=end_created_at,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
        sort_desc=sort_desc,
        limit=effective_limit + 1,
    )
    entries = db.scalars(query).all()

    has_more = len(entries) > effective_limit
    next_cursor_created_at: datetime | None = None
    next_cursor_id: str | None = None
    if has_more:
        entries = entries[:effective_limit]
        next_cursor_created_at = _as_utc(entries[-1].created_at)
        next_cursor_id = entries[-1].id

    return IntakeReplayExportTokenAuditHistoryListResponse(
        items=entries,
        limit=effective_limit,
        has_more=has_more,
        next_cursor_created_at=next_cursor_created_at,
        next_cursor_id=next_cursor_id,
        sort=sort,
    )


@router.get(
    "/events/replay-history/export-token-history/summary",
    response_model=IntakeReplayExportTokenAuditSummaryResponse,
    operation_id="intake_events_replay_history_export_token_history_summary",
    summary="Summarize replay export token audit history",
)
def summarize_replay_export_token_audit_history(
    tenant_id: str | None = Query(default=None),
    token_id: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    action: str | None = Query(
        default=None,
        pattern="^(issue_replay_history_export_token|consume_replay_history_export_token|revoke_replay_history_export_token)$",
    ),
    start_created_at: datetime | None = Query(default=None),
    end_created_at: datetime | None = Query(default=None),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    row = db.execute(
        _build_replay_export_token_audit_summary_query(
            context=context,
            tenant_id=tenant_id,
            token_id=token_id,
            actor_user_id=actor_user_id,
            action=action,
            start_created_at=start_created_at,
            end_created_at=end_created_at,
        )
    ).one()

    issued_count = int(row.issued_count or 0)
    consumed_count = int(row.consumed_count or 0)
    revoked_count = int(row.revoked_count or 0)
    consume_rate_percent: float | None = None
    revoke_rate_percent: float | None = None
    if issued_count > 0:
        consume_rate_percent = round((consumed_count / issued_count) * 100, 2)
        revoke_rate_percent = round((revoked_count / issued_count) * 100, 2)

    return IntakeReplayExportTokenAuditSummaryResponse(
        total_entries=int(row.total_entries or 0),
        issued_count=issued_count,
        consumed_count=consumed_count,
        revoked_count=revoked_count,
        consume_rate_percent=consume_rate_percent,
        revoke_rate_percent=revoke_rate_percent,
        unique_actor_count=int(row.unique_actor_count or 0),
        latest_created_at=_as_utc(row.latest_created_at) if row.latest_created_at else None,
    )


@router.get(
    "/events/replay-history/export-token-history/trends",
    response_model=IntakeReplayExportTokenAuditTrendResponse,
    operation_id="intake_events_replay_history_export_token_history_trends",
    summary="Trend replay export token audit history",
)
def trend_replay_export_token_audit_history(
    tenant_id: str | None = Query(default=None),
    token_id: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    action: str | None = Query(
        default=None,
        pattern="^(issue_replay_history_export_token|consume_replay_history_export_token|revoke_replay_history_export_token)$",
    ),
    start_created_at: datetime | None = Query(default=None),
    end_created_at: datetime | None = Query(default=None),
    granularity: str = Query(default="day", pattern="^(hour|day)$"),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    query = _build_replay_export_token_audit_query(
        context=context,
        tenant_id=tenant_id,
        token_id=token_id,
        actor_user_id=actor_user_id,
        action=action,
        start_created_at=start_created_at,
        end_created_at=end_created_at,
        cursor_created_at=None,
        cursor_id=None,
        sort_desc=False,
        limit=None,
    )
    logs = db.scalars(query).all()
    items = _bucket_replay_export_token_audit_trend(logs=logs, granularity=granularity)

    return IntakeReplayExportTokenAuditTrendResponse(
        items=items,
        granularity=granularity,
        window_start_created_at=start_created_at,
        window_end_created_at=end_created_at,
        window_effective_timezone="UTC",
    )


@router.get(
    "/events/replay-history/export-token-states",
    response_model=list[IntakeReplayExportTokenStateResponse],
    operation_id="intake_events_replay_history_export_token_states",
    summary="List replay export token effective states",
)
def list_replay_export_token_states(
    response: Response,
    tenant_id: str | None = Query(default=None),
    token_id: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    start_issued_at: datetime | None = Query(default=None),
    end_issued_at: datetime | None = Query(default=None),
    cursor_issued_at: datetime | None = Query(default=None),
    cursor_token_id: UUID | None = Query(default=None),
    sort: str = Query(default="-issued_at", pattern=r"^(-issued_at|\+issued_at)$"),
    limit: int = Query(default=100, ge=1, le=500),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    response.headers["X-Window-Effective-Timezone"] = "UTC"

    sort_desc = sort == "-issued_at"
    issue_query = _build_replay_export_token_issue_query(
        context=context,
        tenant_id=tenant_id,
        token_id=token_id,
        actor_user_id=actor_user_id,
        start_issued_at=start_issued_at,
        end_issued_at=end_issued_at,
        cursor_issued_at=cursor_issued_at,
        cursor_token_id=cursor_token_id,
        sort_desc=sort_desc,
        limit=limit + 1,
    )

    issue_logs = db.scalars(issue_query).all()
    has_more = len(issue_logs) > limit
    if has_more:
        issue_logs = issue_logs[:limit]
        response.headers["X-Next-Cursor-Issued-At"] = issue_logs[-1].created_at.isoformat()
        response.headers["X-Next-Cursor-Token-Id"] = issue_logs[-1].resource_id

    return _project_replay_export_token_states(db=db, issue_logs=issue_logs)


@router.get(
    "/events/replay-history/export-token-states/list",
    response_model=IntakeReplayExportTokenStateListResponse,
    operation_id="intake_events_replay_history_export_token_states_list",
    summary="List replay export token effective states with window metadata",
)
def list_replay_export_token_states_with_window(
    tenant_id: str | None = Query(default=None),
    token_id: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    start_issued_at: datetime | None = Query(default=None),
    end_issued_at: datetime | None = Query(default=None),
    cursor_issued_at: datetime | None = Query(default=None),
    cursor_token_id: UUID | None = Query(default=None),
    sort: str = Query(default="-issued_at", pattern=r"^(-issued_at|\+issued_at)$"),
    limit: int = Query(default=100, ge=1, le=500),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    sort_desc = sort == "-issued_at"
    issue_query = _build_replay_export_token_issue_query(
        context=context,
        tenant_id=tenant_id,
        token_id=token_id,
        actor_user_id=actor_user_id,
        start_issued_at=start_issued_at,
        end_issued_at=end_issued_at,
        cursor_issued_at=cursor_issued_at,
        cursor_token_id=cursor_token_id,
        sort_desc=sort_desc,
        limit=limit + 1,
    )

    issue_logs = db.scalars(issue_query).all()
    has_more = len(issue_logs) > limit
    next_cursor_issued_at: datetime | None = None
    next_cursor_token_id: str | None = None
    if has_more:
        issue_logs = issue_logs[:limit]
        next_cursor_issued_at = _as_utc(issue_logs[-1].created_at)
        next_cursor_token_id = issue_logs[-1].resource_id

    states = _project_replay_export_token_states(db=db, issue_logs=issue_logs)
    return IntakeReplayExportTokenStateListResponse(
        items=states,
        limit=limit,
        has_more=has_more,
        next_cursor_issued_at=next_cursor_issued_at,
        next_cursor_token_id=next_cursor_token_id,
        sort=sort,
        window_start_issued_at=_as_utc(start_issued_at) if start_issued_at else None,
        window_end_issued_at=_as_utc(end_issued_at) if end_issued_at else None,
        window_effective_timezone="UTC",
    )


@router.get(
    "/events/replay-history/export-token-states/summary",
    response_model=IntakeReplayExportTokenStateSummaryResponse,
    operation_id="intake_events_replay_history_export_token_states_summary",
    summary="Summarize replay export token effective states",
)
def summarize_replay_export_token_states(
    tenant_id: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    start_issued_at: datetime | None = Query(default=None),
    end_issued_at: datetime | None = Query(default=None),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    issue_query = _build_replay_export_token_issue_query(
        context=context,
        tenant_id=tenant_id,
        token_id=None,
        actor_user_id=actor_user_id,
        start_issued_at=start_issued_at,
        end_issued_at=end_issued_at,
        cursor_issued_at=None,
        cursor_token_id=None,
        sort_desc=True,
        limit=None,
    )
    issue_logs = db.scalars(issue_query).all()
    normalized_start_issued_at = _as_utc(start_issued_at) if start_issued_at else None
    normalized_end_issued_at = _as_utc(end_issued_at) if end_issued_at else None
    if not issue_logs:
        return IntakeReplayExportTokenStateSummaryResponse(
            window_start_issued_at=normalized_start_issued_at,
            window_end_issued_at=normalized_end_issued_at,
            window_effective_timezone="UTC",
            total_tokens=0,
            issued_tokens=0,
            consumed_tokens=0,
            revoked_tokens=0,
            expired_tokens=0,
            actors=[],
        )

    states = _project_replay_export_token_states(db=db, issue_logs=issue_logs)
    issued_count = 0
    consumed_count = 0
    revoked_count = 0
    expired_count = 0

    actor_totals: dict[str, dict[str, int]] = {}

    for state_entry in states:
        state = state_entry.state
        if state == "revoked":
            revoked_count += 1
        elif state == "consumed":
            consumed_count += 1
        elif state == "expired":
            expired_count += 1
        else:
            issued_count += 1

        actor_bucket = actor_totals.setdefault(
            state_entry.issued_by_user_id,
            {
                "total_tokens": 0,
                "issued_tokens": 0,
                "consumed_tokens": 0,
                "revoked_tokens": 0,
                "expired_tokens": 0,
            },
        )
        actor_bucket["total_tokens"] += 1
        actor_bucket[f"{state}_tokens"] += 1

    actor_summaries = [
        IntakeReplayExportTokenActorStateSummaryResponse(
            actor_user_id=actor,
            total_tokens=bucket["total_tokens"],
            issued_tokens=bucket["issued_tokens"],
            consumed_tokens=bucket["consumed_tokens"],
            revoked_tokens=bucket["revoked_tokens"],
            expired_tokens=bucket["expired_tokens"],
        )
        for actor, bucket in sorted(
            actor_totals.items(),
            key=lambda item: (-item[1]["total_tokens"], item[0]),
        )
    ]

    return IntakeReplayExportTokenStateSummaryResponse(
        window_start_issued_at=normalized_start_issued_at,
        window_end_issued_at=normalized_end_issued_at,
        window_effective_timezone="UTC",
        total_tokens=len(issue_logs),
        issued_tokens=issued_count,
        consumed_tokens=consumed_count,
        revoked_tokens=revoked_count,
        expired_tokens=expired_count,
        actors=actor_summaries,
    )


@router.get(
    "/events/replay-history/export",
    operation_id="intake_events_replay_history_export",
    summary="Export dead-letter replay audit history",
)
def export_replay_dead_letter_audit_history(
    tenant_id: str | None = Query(default=None),
    event_id: str | None = Query(default=None),
    start_created_at: datetime | None = Query(default=None),
    end_created_at: datetime | None = Query(default=None),
    cursor_created_at: datetime | None = Query(default=None),
    output: str = Query(default="csv", pattern="^(csv|json)$"),
    limit: int = Query(default=100, ge=1, le=500),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    return _render_replay_audit_history_export_response(
        context=context,
        db=db,
        tenant_id=tenant_id,
        event_id=event_id,
        start_created_at=start_created_at,
        end_created_at=end_created_at,
        cursor_created_at=cursor_created_at,
        output=output,
        limit=limit,
    )


@router.post(
    "/events/replay-history/export-token",
    response_model=IntakeReplayExportTokenResponse,
    operation_id="intake_events_replay_history_export_token",
    summary="Generate signed replay-history export token",
)
def create_replay_dead_letter_export_token(
    tenant_id: str | None = Query(default=None),
    event_id: str | None = Query(default=None),
    start_created_at: datetime | None = Query(default=None),
    end_created_at: datetime | None = Query(default=None),
    cursor_created_at: datetime | None = Query(default=None),
    output: str = Query(default="csv", pattern="^(csv|json)$"),
    limit: int = Query(default=100, ge=1, le=500),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    _validate_replay_audit_history_date_range(
        start_created_at=start_created_at,
        end_created_at=end_created_at,
    )
    tenant_scope = _resolve_replay_export_tenant_scope(
        context=context,
        requested_tenant_id=tenant_id,
    )
    token_id = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.INTAKE_REPLAY_EXPORT_TOKEN_MINUTES
    )
    token_payload = {
        "type": "replay_history_export_download",
        "sub": context.user.id,
        "tenant_id": tenant_scope,
        "event_id": event_id,
        "start_created_at": start_created_at.isoformat() if start_created_at else None,
        "end_created_at": end_created_at.isoformat() if end_created_at else None,
        "cursor_created_at": cursor_created_at.isoformat() if cursor_created_at else None,
        "output": output,
        "limit": limit,
        "jti": token_id,
    }
    export_token = create_token(
        token_payload,
        expires_minutes=settings.INTAKE_REPLAY_EXPORT_TOKEN_MINUTES,
    )

    db.add(
        AuditLog(
            tenant_id=tenant_scope,
            actor_user_id=context.user.id,
            action="issue_replay_history_export_token",
            resource_type="replay_history_export_token",
            resource_id=token_id,
            details=(
                "Issued signed replay-history export token. "
                f"event_id={event_id or 'all'}; output={output}; limit={limit}"
            ),
            created_by=context.user.id,
        )
    )
    db.commit()

    return IntakeReplayExportTokenResponse(
        token=export_token,
        download_url=f"/api/intake/events/replay-history/export/download?token={export_token}",
        expires_at=expires_at,
    )


@router.get(
    "/events/replay-history/export/download",
    operation_id="intake_events_replay_history_export_download",
    summary="Download replay-history export with signed token",
)
def download_replay_dead_letter_audit_history_export(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    try:
        token_payload = decode_token(token)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid export token") from exc

    if token_payload.get("type") != "replay_history_export_download":
        raise HTTPException(status_code=401, detail="Invalid export token")

    token_id = token_payload.get("jti")
    actor_user_id = token_payload.get("sub")
    tenant_id = token_payload.get("tenant_id")

    if not isinstance(token_id, str) or not isinstance(actor_user_id, str) or not isinstance(tenant_id, str):
        raise HTTPException(status_code=401, detail="Invalid export token")

    revoked = db.scalar(
        select(AuditLog.id)
        .where(AuditLog.action == "revoke_replay_history_export_token")
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.resource_id == token_id)
        .limit(1)
    )
    if revoked:
        raise HTTPException(status_code=410, detail="Export token has been revoked")

    prior_use = db.scalar(
        select(AuditLog.id)
        .where(AuditLog.action == "consume_replay_history_export_token")
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.resource_id == token_id)
        .limit(1)
    )
    if prior_use:
        raise HTTPException(status_code=410, detail="Export token has already been used")

    user = db.get(User, actor_user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid export token")

    output = token_payload.get("output")
    if output not in {"csv", "json"}:
        raise HTTPException(status_code=400, detail="Invalid output in export token")

    limit = token_payload.get("limit")
    if not isinstance(limit, int) or limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="Invalid limit in export token")

    event_id = token_payload.get("event_id")
    if event_id is not None and not isinstance(event_id, str):
        raise HTTPException(status_code=400, detail="Invalid event_id in export token")

    start_created_at = _parse_export_token_datetime(
        value=token_payload.get("start_created_at"),
        field_name="start_created_at",
    )
    end_created_at = _parse_export_token_datetime(
        value=token_payload.get("end_created_at"),
        field_name="end_created_at",
    )
    cursor_created_at = _parse_export_token_datetime(
        value=token_payload.get("cursor_created_at"),
        field_name="cursor_created_at",
    )

    token_context = RequestContext(
        user=user,
        membership=None,
        permissions={"*"},
        tenant_id=tenant_id,
    )
    response = _render_replay_audit_history_export_response(
        context=token_context,
        db=db,
        tenant_id=tenant_id,
        event_id=event_id,
        start_created_at=start_created_at,
        end_created_at=end_created_at,
        cursor_created_at=cursor_created_at,
        output=output,
        limit=limit,
    )

    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action="consume_replay_history_export_token",
            resource_type="replay_history_export_token",
            resource_id=token_id,
            details=(
                "Consumed signed replay-history export token. "
                f"event_id={event_id or 'all'}; output={output}; limit={limit}"
            ),
            created_by=actor_user_id,
        )
    )
    db.commit()

    return response


@router.post(
    "/events/replay-history/export-token/revoke",
    response_model=IntakeReplayExportTokenRevokeResponse,
    operation_id="intake_events_replay_history_export_token_revoke",
    summary="Revoke signed replay-history export token",
)
def revoke_replay_dead_letter_export_token(
    payload: IntakeReplayExportTokenRevokeRequest,
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    try:
        token_payload = decode_token(payload.token)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid export token") from exc

    if token_payload.get("type") != "replay_history_export_download":
        raise HTTPException(status_code=401, detail="Invalid export token")

    token_id = token_payload.get("jti")
    actor_user_id = token_payload.get("sub")
    token_tenant_id = token_payload.get("tenant_id")

    if not isinstance(token_id, str) or not isinstance(actor_user_id, str) or not isinstance(token_tenant_id, str):
        raise HTTPException(status_code=401, detail="Invalid export token")

    if "*" in context.permissions:
        if context.tenant_id and context.tenant_id != token_tenant_id:
            raise HTTPException(status_code=403, detail="Cannot revoke export token for another tenant")
    else:
        assert context.membership is not None
        if context.membership.tenant_id != token_tenant_id:
            raise HTTPException(status_code=403, detail="Cannot revoke export token for another tenant")

    if context.user.id != actor_user_id and "*" not in context.permissions:
        raise HTTPException(status_code=403, detail="Cannot revoke another user's export token")

    consumed = db.scalar(
        select(AuditLog.id)
        .where(AuditLog.action == "consume_replay_history_export_token")
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.resource_id == token_id)
        .limit(1)
    )
    if consumed:
        raise HTTPException(status_code=409, detail="Export token has already been consumed")

    already_revoked = db.scalar(
        select(AuditLog.id)
        .where(AuditLog.action == "revoke_replay_history_export_token")
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.resource_id == token_id)
        .limit(1)
    )
    if already_revoked:
        raise HTTPException(status_code=409, detail="Export token has already been revoked")

    revoked_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            tenant_id=token_tenant_id,
            actor_user_id=context.user.id,
            action="revoke_replay_history_export_token",
            resource_type="replay_history_export_token",
            resource_id=token_id,
            details="Revoked signed replay-history export token before consumption.",
            created_by=context.user.id,
            created_at=revoked_at,
            updated_at=revoked_at,
        )
    )
    db.commit()

    return IntakeReplayExportTokenRevokeResponse(
        token_id=token_id,
        revoked=True,
        revoked_at=revoked_at,
    )


@router.post(
    "/events/replay-history/export-token/revoke-active",
    response_model=IntakeReplayExportTokenBulkRevokeActiveResponse,
    operation_id="intake_events_replay_history_export_token_revoke_active",
    summary="Bulk revoke active signed replay-history export tokens",
)
def revoke_active_replay_dead_letter_export_tokens(
    payload: IntakeReplayExportTokenBulkRevokeActiveRequest,
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    tenant_scope = _resolve_replay_export_tenant_scope(
        context=context,
        requested_tenant_id=payload.tenant_id,
        required_purpose="bulk replay export token revocation",
    )
    if not payload.dry_run and "*" not in context.permissions and "intake_review" not in context.permissions:
        raise HTTPException(
            status_code=403,
            detail="Live bulk token revocation requires intake_review permission",
        )

    normalized_reason = (payload.reason or "").strip()
    if not payload.dry_run and not normalized_reason:
        raise HTTPException(
            status_code=400,
            detail="reason is required when dry_run=false",
        )

    issue_query = (
        select(AuditLog)
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.action == "issue_replay_history_export_token")
        .where(AuditLog.tenant_id == tenant_scope)
        .order_by(AuditLog.created_at.desc())
        .limit(payload.limit)
    )
    if payload.actor_user_id:
        issue_query = issue_query.where(AuditLog.actor_user_id == payload.actor_user_id)
    if payload.issued_before:
        issue_query = issue_query.where(AuditLog.created_at <= payload.issued_before)

    issue_logs = db.scalars(issue_query).all()
    if not issue_logs:
        return IntakeReplayExportTokenBulkRevokeActiveResponse(
            tenant_id=tenant_scope,
            dry_run=payload.dry_run,
            inspected_tokens=0,
            candidate_count=0,
            revoked_count=0,
            skipped_consumed_count=0,
            skipped_revoked_count=0,
            skipped_expired_count=0,
            candidate_token_ids=[],
            revoked_token_ids=[],
            revoked_at=datetime.now(timezone.utc),
        )

    token_ids = [log.resource_id for log in issue_logs]
    lifecycle_logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.resource_id.in_(token_ids))
        .where(
            AuditLog.action.in_(
                (
                    "consume_replay_history_export_token",
                    "revoke_replay_history_export_token",
                )
            )
        )
        .order_by(AuditLog.created_at.desc())
    ).all()

    consumed_token_ids: set[str] = set()
    revoked_token_ids: set[str] = set()
    for log in lifecycle_logs:
        if log.action == "consume_replay_history_export_token":
            consumed_token_ids.add(log.resource_id)
        if log.action == "revoke_replay_history_export_token":
            revoked_token_ids.add(log.resource_id)

    now_utc = datetime.now(timezone.utc)
    revoked_at = now_utc
    revoke_reason = normalized_reason or "Bulk incident-response revocation of active token"
    candidate_token_ids: list[str] = []
    newly_revoked_token_ids: list[str] = []
    skipped_consumed_count = 0
    skipped_revoked_count = 0
    skipped_expired_count = 0

    for issue in issue_logs:
        token_id = issue.resource_id
        if token_id in revoked_token_ids:
            skipped_revoked_count += 1
            continue
        if token_id in consumed_token_ids:
            skipped_consumed_count += 1
            continue

        expires_at = _as_utc(issue.created_at) + timedelta(
            minutes=settings.INTAKE_REPLAY_EXPORT_TOKEN_MINUTES
        )
        if expires_at < now_utc:
            skipped_expired_count += 1
            continue

        candidate_token_ids.append(token_id)
        if payload.dry_run:
            continue

        db.add(
            AuditLog(
                tenant_id=tenant_scope,
                actor_user_id=context.user.id,
                action="revoke_replay_history_export_token",
                resource_type="replay_history_export_token",
                resource_id=token_id,
                details=(
                    "Bulk revoked signed replay-history export token before consumption. "
                    f"reason={revoke_reason}"
                ),
                created_by=context.user.id,
                created_at=revoked_at,
                updated_at=revoked_at,
            )
        )
        newly_revoked_token_ids.append(token_id)

    if not payload.dry_run and newly_revoked_token_ids:
        db.commit()

    return IntakeReplayExportTokenBulkRevokeActiveResponse(
        tenant_id=tenant_scope,
        dry_run=payload.dry_run,
        inspected_tokens=len(issue_logs),
        candidate_count=len(candidate_token_ids),
        revoked_count=len(newly_revoked_token_ids),
        skipped_consumed_count=skipped_consumed_count,
        skipped_revoked_count=skipped_revoked_count,
        skipped_expired_count=skipped_expired_count,
        candidate_token_ids=candidate_token_ids,
        revoked_token_ids=newly_revoked_token_ids,
        revoked_at=revoked_at,
    )


@router.get(
    "/events/replay-history/export-token-states/alerts",
    response_model=IntakeReplayExportTokenStateAlertsResponse,
    operation_id="intake_events_replay_history_export_token_states_alerts",
    summary="Summarize replay export token alert thresholds",
)
def replay_export_token_state_alerts(
    tenant_id: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    start_issued_at: datetime | None = Query(default=None),
    end_issued_at: datetime | None = Query(default=None),
    stale_threshold_minutes: int = Query(default=60, ge=1, le=10080),
    stale_active_threshold_count: int = Query(default=10, ge=1, le=10000),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    issue_query = _build_replay_export_token_issue_query(
        context=context,
        tenant_id=tenant_id,
        token_id=None,
        actor_user_id=actor_user_id,
        start_issued_at=start_issued_at,
        end_issued_at=end_issued_at,
        cursor_issued_at=None,
        cursor_token_id=None,
        sort_desc=True,
        limit=None,
    )
    issue_logs = db.scalars(issue_query).all()
    states = _project_replay_export_token_states(db=db, issue_logs=issue_logs)

    as_of = datetime.now(timezone.utc)
    stale_cutoff = as_of - timedelta(minutes=stale_threshold_minutes)
    active_tokens = [entry for entry in states if entry.state == "issued"]
    stale_active_tokens = [entry for entry in active_tokens if _as_utc(entry.issued_at) <= stale_cutoff]
    consumed_tokens = [entry for entry in states if entry.state == "consumed"]
    revoked_tokens = [entry for entry in states if entry.state == "revoked"]
    consumed_to_revoked_ratio: float | None = None
    if revoked_tokens:
        consumed_to_revoked_ratio = len(consumed_tokens) / len(revoked_tokens)

    return IntakeReplayExportTokenStateAlertsResponse(
        as_of=as_of,
        stale_threshold_minutes=stale_threshold_minutes,
        stale_active_threshold_count=stale_active_threshold_count,
        window_start_issued_at=_as_utc(start_issued_at) if start_issued_at else None,
        window_end_issued_at=_as_utc(end_issued_at) if end_issued_at else None,
        window_effective_timezone="UTC",
        total_tokens=len(states),
        active_tokens=len(active_tokens),
        active_tokens_older_than_threshold=len(stale_active_tokens),
        active_tokens_older_than_threshold_exceeded=(
            len(stale_active_tokens) >= stale_active_threshold_count
        ),
        consumed_tokens=len(consumed_tokens),
        revoked_tokens=len(revoked_tokens),
        consumed_to_revoked_ratio=consumed_to_revoked_ratio,
    )
