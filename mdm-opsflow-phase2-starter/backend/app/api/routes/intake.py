from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import IntakeItem, IntakeStatus
from app.schemas import IntakeItemResponse
from app.services.intake_processing import process_intake_upload


router = APIRouter(prefix="/api/intake", tags=["Intake Hub"])


def _tenant_id_from_context(context: RequestContext) -> str:
    if context.tenant_id:
        return context.tenant_id
    if context.membership:
        return context.membership.tenant_id
    raise HTTPException(status_code=400, detail="X-Tenant-ID is required for platform admins")


@router.get(
    "/items",
    response_model=list[IntakeItemResponse],
    operation_id="intake_items_list",
    summary="List intake items",
)
def list_intake_items(
    tenant_id: str | None = Query(default=None),
    context: RequestContext = Depends(require_permissions("intake_read")),
    db: Session = Depends(get_db),
):
    if "*" in context.permissions:
        if tenant_id:
            return db.scalars(select(IntakeItem).where(IntakeItem.tenant_id == tenant_id)).all()
        return db.scalars(select(IntakeItem)).all()

    assert context.membership is not None
    return db.scalars(select(IntakeItem).where(IntakeItem.tenant_id == context.membership.tenant_id)).all()


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
    item = db.get(IntakeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Intake item not found")

    if "*" not in context.permissions and (
        not context.membership or item.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Intake item not found")

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

    processed = process_intake_upload(
        tenant_id=tenant_id,
        original_filename=original_filename,
        mime_type=file.content_type or "application/octet-stream",
        payload=payload,
    )

    item = IntakeItem(
        tenant_id=tenant_id,
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
        classification_confidence=processed.classification_confidence,
        match_confidence=processed.match_confidence,
        conflict_notes="",
        created_by=context.user.id,
    )

    db.add(item)
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
    item = db.get(IntakeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Intake item not found")

    if "*" not in context.permissions and (
        not context.membership or item.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Intake item not found")

    item.status = IntakeStatus.APPROVED
    item.needs_review = False
    item.reviewed_by = context.user.id
    item.reviewed_at = datetime.utcnow()

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
    item = db.get(IntakeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Intake item not found")

    if "*" not in context.permissions and (
        not context.membership or item.tenant_id != context.membership.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Intake item not found")

    item.status = IntakeStatus.REJECTED
    item.needs_review = True
    item.review_reason = reason or "Rejected by reviewer"
    item.reviewed_by = context.user.id
    item.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(item)
    return item
