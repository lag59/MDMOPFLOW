from __future__ import annotations

from datetime import datetime
import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
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
)
from app.schemas import (
    IntakeDuplicateResolutionRequest,
    IntakeIntegrationEventProcessRequest,
    IntakeIntegrationEventRetryRequest,
    IntakeIntegrationEventResponse,
    IntakeItemResponse,
)
from app.services.intake_processing import process_intake_upload


router = APIRouter(prefix="/api/intake", tags=["Intake Hub"])


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
    retry_count = int(event_payload.get("retry_count") or 0) + 1
    event_payload["retry_count"] = retry_count
    event_payload["last_retry_by"] = context.user.id
    event_payload["last_retry_notes"] = payload.retry_notes.strip()
    event_payload.pop("failure_reason", None)

    event.status = "pending"
    event.payload_json = json.dumps(event_payload)
    event.processed_at = None

    db.commit()
    db.refresh(event)
    return event
