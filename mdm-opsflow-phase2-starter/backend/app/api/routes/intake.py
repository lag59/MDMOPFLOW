from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
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
    IntakeDuplicateResolutionRequest,
    IntakeIntegrationEventProcessRequest,
    IntakeIntegrationEventReplayRequest,
    IntakeReplayExportTokenAuditEntryResponse,
    IntakeReplayExportTokenBulkRevokeActiveRequest,
    IntakeReplayExportTokenBulkRevokeActiveResponse,
    IntakeReplayExportTokenActorStateSummaryResponse,
    IntakeReplayExportTokenStateResponse,
    IntakeReplayExportTokenStateSummaryResponse,
    IntakeReplayExportTokenRevokeRequest,
    IntakeReplayExportTokenRevokeResponse,
    IntakeReplayExportTokenResponse,
    IntakeReplayAuditEntryResponse,
    IntakeIntegrationEventRetryRequest,
    IntakeIntegrationEventResponse,
    IntakeItemResponse,
)
from app.security import TokenError, create_token, decode_token
from app.core.config import settings
from app.services.intake_processing import process_intake_upload


router = APIRouter(prefix="/api/intake", tags=["Intake Hub"])
MAX_INTEGRATION_EVENT_RETRIES = 3
REPLAY_EXPORT_TOKEN_AUDIT_ACTIONS = (
    "issue_replay_history_export_token",
    "consume_replay_history_export_token",
    "revoke_replay_history_export_token",
)
_TOKEN_ISSUE_DETAILS_PATTERN = re.compile(r"event_id=(.*?); output=(.*?); limit=(\d+)$")


def _tenant_id_from_context(context: RequestContext) -> str:
    if context.tenant_id:
        return context.tenant_id
    if context.membership:
        return context.membership.tenant_id
    raise HTTPException(status_code=400, detail="X-Tenant-ID is required for platform admins")


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

    assert context.membership is not None
    query = query.where(IntakeItem.tenant_id == context.membership.tenant_id)
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
    if ticket_number and not is_duplicate:
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
    return item


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
        assert context.membership is not None
        query = query.where(IntegrationEvent.tenant_id == context.membership.tenant_id)

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

    if "*" in context.permissions:
        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)
    else:
        assert context.membership is not None
        query = query.where(AuditLog.tenant_id == context.membership.tenant_id)

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
    if "*" in context.permissions:
        if requested_tenant_id:
            return requested_tenant_id
        raise HTTPException(
            status_code=400,
            detail=f"tenant_id is required for {required_purpose}",
        )

    assert context.membership is not None
    if requested_tenant_id and requested_tenant_id != context.membership.tenant_id:
        raise HTTPException(status_code=403, detail="Cannot export replay history for another tenant")
    return context.membership.tenant_id


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
    limit: int,
):
    _validate_replay_audit_history_date_range(
        start_created_at=start_created_at,
        end_created_at=end_created_at,
    )

    query = (
        select(AuditLog)
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.action.in_(REPLAY_EXPORT_TOKEN_AUDIT_ACTIONS))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )

    if "*" in context.permissions:
        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)
    else:
        assert context.membership is not None
        query = query.where(AuditLog.tenant_id == context.membership.tenant_id)

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
        query = query.where(AuditLog.created_at < cursor_created_at)

    return query


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
    limit: int = Query(default=100, ge=1, le=500),
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
    limit: int = Query(default=100, ge=1, le=500),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    _validate_replay_audit_history_date_range(
        start_created_at=start_issued_at,
        end_created_at=end_issued_at,
    )

    issue_query = (
        select(AuditLog)
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.action == "issue_replay_history_export_token")
        .order_by(AuditLog.created_at.desc())
        .limit(limit + 1)
    )

    if "*" in context.permissions:
        if tenant_id:
            issue_query = issue_query.where(AuditLog.tenant_id == tenant_id)
    else:
        assert context.membership is not None
        issue_query = issue_query.where(AuditLog.tenant_id == context.membership.tenant_id)

    if token_id:
        issue_query = issue_query.where(AuditLog.resource_id == token_id)

    if actor_user_id:
        issue_query = issue_query.where(AuditLog.actor_user_id == actor_user_id)

    if start_issued_at:
        issue_query = issue_query.where(AuditLog.created_at >= start_issued_at)

    if end_issued_at:
        issue_query = issue_query.where(AuditLog.created_at <= end_issued_at)

    if cursor_issued_at:
        issue_query = issue_query.where(AuditLog.created_at < cursor_issued_at)

    issue_logs = db.scalars(issue_query).all()
    has_more = len(issue_logs) > limit
    if has_more:
        issue_logs = issue_logs[:limit]
        response.headers["X-Next-Cursor-Issued-At"] = issue_logs[-1].created_at.isoformat()

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
    _validate_replay_audit_history_date_range(
        start_created_at=start_issued_at,
        end_created_at=end_issued_at,
    )

    issue_query = (
        select(AuditLog)
        .where(AuditLog.resource_type == "replay_history_export_token")
        .where(AuditLog.action == "issue_replay_history_export_token")
        .order_by(AuditLog.created_at.desc())
    )

    if "*" in context.permissions:
        if tenant_id:
            issue_query = issue_query.where(AuditLog.tenant_id == tenant_id)
    else:
        assert context.membership is not None
        issue_query = issue_query.where(AuditLog.tenant_id == context.membership.tenant_id)

    if actor_user_id:
        issue_query = issue_query.where(AuditLog.actor_user_id == actor_user_id)

    if start_issued_at:
        issue_query = issue_query.where(AuditLog.created_at >= start_issued_at)

    if end_issued_at:
        issue_query = issue_query.where(AuditLog.created_at <= end_issued_at)

    issue_logs = db.scalars(issue_query).all()
    if not issue_logs:
        return IntakeReplayExportTokenStateSummaryResponse(
            window_start_issued_at=start_issued_at,
            window_end_issued_at=end_issued_at,
            total_tokens=0,
            issued_tokens=0,
            consumed_tokens=0,
            revoked_tokens=0,
            expired_tokens=0,
            actors=[],
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

    consume_by_token_id: dict[str, AuditLog] = {}
    revoke_by_token_id: dict[str, AuditLog] = {}
    for log in lifecycle_logs:
        if log.action == "consume_replay_history_export_token" and log.resource_id not in consume_by_token_id:
            consume_by_token_id[log.resource_id] = log
        if log.action == "revoke_replay_history_export_token" and log.resource_id not in revoke_by_token_id:
            revoke_by_token_id[log.resource_id] = log

    now_utc = datetime.now(timezone.utc)
    issued_count = 0
    consumed_count = 0
    revoked_count = 0
    expired_count = 0

    actor_totals: dict[str, dict[str, int]] = {}

    for issue in issue_logs:
        consumed = consume_by_token_id.get(issue.resource_id)
        revoked = revoke_by_token_id.get(issue.resource_id)
        issued_at_utc = _as_utc(issue.created_at)
        expires_at = issued_at_utc + timedelta(minutes=settings.INTAKE_REPLAY_EXPORT_TOKEN_MINUTES)

        state = "issued"
        if revoked is not None:
            state = "revoked"
            revoked_count += 1
        elif consumed is not None:
            state = "consumed"
            consumed_count += 1
        elif expires_at < now_utc:
            state = "expired"
            expired_count += 1
        else:
            issued_count += 1

        actor_bucket = actor_totals.setdefault(
            issue.actor_user_id,
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
        window_start_issued_at=start_issued_at,
        window_end_issued_at=end_issued_at,
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
    revoke_reason = (payload.reason or "").strip() or "Bulk incident-response revocation of active token"
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
