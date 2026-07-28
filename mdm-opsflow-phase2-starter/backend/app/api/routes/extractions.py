"""API routes for document extraction review and approval."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.schemas import (
    DocumentExtractionIssueResponse,
    DocumentExtractionResponse,
    ExtractionApprovalRequest,
    ExtractionApprovalResponse,
    ExtractionDetailResponse,
    ExtractionListResponse,
    ExtractionListItemResponse,
    ExtractionReviewRequest,
    ExtractionTriggerResponse,
)
from app.services.extraction_review import ExtractionReviewService
from app.services.extraction_approval import ExtractionApprovalService
from app.services.ocr_extraction_service import OCRExtractionService

router = APIRouter(prefix="/api/extractions", tags=["Extractions"])


@router.get(
    "",
    response_model=ExtractionListResponse,
    summary="List pending extractions",
    description="Get list of extractions pending review or approval.",
)
def list_pending_extractions(
    context: RequestContext = Depends(require_permissions("extraction_read")),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: str = Query("review_pending", pattern="^(review_pending|review_submitted|approved|rejected|distributed)$"),
    status: str | None = Query(None, pattern="^(review_pending|review_submitted|approved|rejected|distributed)$"),
):
    """List extractions by status."""
    tenant_id = context.tenant_id or context.membership.tenant_id
    service = ExtractionReviewService(db, context.user.id, tenant_id)
    effective_status = status or status_filter

    if effective_status == "review_pending":
        extractions, total = service.get_pending_review_extractions(limit, offset)
    elif effective_status == "review_submitted":
        extractions, total = service.get_submitted_review_extractions(limit, offset)
    else:
        extractions, total = service.get_extractions_by_status(effective_status, limit, offset)

    # Calculate confidence scores and issue counts
    items = []
    for extraction in extractions:
        avg_confidence = service.calculate_extraction_confidence_score(extraction)
        issues = service.get_extraction_issues(extraction.id)
        issue_count = len([i for i in issues if not i.resolved])

        item = ExtractionListItemResponse(
            id=extraction.id,
            status=extraction.status,
            document_type=extraction.document_type,
            company_name=extraction.company_name,
            ticket_number=extraction.ticket_number,
            issue_count=issue_count,
            avg_confidence=avg_confidence,
            created_at=extraction.created_at,
        )
        items.append(item)

    return ExtractionListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{extraction_id}",
    response_model=ExtractionDetailResponse,
    summary="Get extraction detail",
    description="Get complete extraction with all issues.",
)
def get_extraction_detail(
    extraction_id: UUID,
    context: RequestContext = Depends(require_permissions("extraction_read")),
    db: Session = Depends(get_db),
):
    """Get extraction detail for review."""
    tenant_id = context.tenant_id or context.membership.tenant_id
    service = ExtractionReviewService(db, context.user.id, tenant_id)
    extraction = service.get_extraction_for_review(extraction_id)

    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    issues = service.get_extraction_issues(extraction_id)

    extraction_response = DocumentExtractionResponse(
        id=extraction.id,
        tenant_id=extraction.tenant_id,
        intake_item_id=extraction.intake_item_id,
        document_type=extraction.document_type,
        document_type_confidence=extraction.document_type_confidence,
        status=extraction.status,
        company_name=extraction.company_name,
        company_name_confidence=extraction.company_name_confidence,
        ticket_number=extraction.ticket_number,
        ticket_number_confidence=extraction.ticket_number_confidence,
        destination=extraction.destination,
        destination_confidence=extraction.destination_confidence,
        material=extraction.material,
        material_confidence=extraction.material_confidence,
        tons=extraction.tons,
        invoice_total=extraction.invoice_total,
        review_notes=extraction.review_notes,
        created_at=extraction.created_at,
        created_by=extraction.created_by,
    )

    issues_response = [
        DocumentExtractionIssueResponse(
            id=issue.id,
            issue_type=issue.issue_type,
            field_name=issue.field_name,
            severity=issue.severity,
            message=issue.message,
            suggested_value=issue.suggested_value,
            correction_source=issue.correction_source,
            resolved=issue.resolved,
            resolved_value=issue.resolved_value,
        )
        for issue in issues
    ]

    return ExtractionDetailResponse(
        extraction=extraction_response,
        issues=issues_response,
    )


@router.post(
    "/{extraction_id}/review",
    response_model=ExtractionDetailResponse,
    summary="Submit extraction review",
    description="Review extraction and apply corrections.",
)
def submit_extraction_review(
    extraction_id: UUID,
    request: ExtractionReviewRequest,
    context: RequestContext = Depends(require_permissions("extraction_review")),
    db: Session = Depends(get_db),
):
    """Submit human review with corrections."""
    tenant_id = context.tenant_id or context.membership.tenant_id
    service = ExtractionReviewService(db, context.user.id, tenant_id)

    try:
        extraction = service.submit_review(
            extraction_id,
            request.review_notes,
            request.corrections,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get updated extraction with issues
    extraction = service.get_extraction_for_review(extraction_id)
    issues = service.get_extraction_issues(extraction_id)

    extraction_response = DocumentExtractionResponse(
        id=extraction.id,
        tenant_id=extraction.tenant_id,
        intake_item_id=extraction.intake_item_id,
        document_type=extraction.document_type,
        document_type_confidence=extraction.document_type_confidence,
        status=extraction.status,
        company_name=extraction.company_name,
        company_name_confidence=extraction.company_name_confidence,
        ticket_number=extraction.ticket_number,
        ticket_number_confidence=extraction.ticket_number_confidence,
        destination=extraction.destination,
        destination_confidence=extraction.destination_confidence,
        material=extraction.material,
        material_confidence=extraction.material_confidence,
        tons=extraction.tons,
        invoice_total=extraction.invoice_total,
        review_notes=extraction.review_notes,
        created_at=extraction.created_at,
        created_by=extraction.created_by,
    )

    issues_response = [
        DocumentExtractionIssueResponse(
            id=issue.id,
            issue_type=issue.issue_type,
            field_name=issue.field_name,
            severity=issue.severity,
            message=issue.message,
            suggested_value=issue.suggested_value,
            correction_source=issue.correction_source,
            resolved=issue.resolved,
            resolved_value=issue.resolved_value,
        )
        for issue in issues
    ]

    return ExtractionDetailResponse(
        extraction=extraction_response,
        issues=issues_response,
    )


@router.post(
    "/{extraction_id}/approve",
    response_model=ExtractionApprovalResponse,
    summary="Approve extraction",
    description="Approve extraction and distribute data to platform systems.",
)
def approve_extraction(
    extraction_id: UUID,
    request: ExtractionApprovalRequest,
    context: RequestContext = Depends(require_permissions("extraction_approve")),
    db: Session = Depends(get_db),
):
    """Approve extraction for distribution."""
    tenant_id = context.tenant_id or context.membership.tenant_id

    if not request.approve:
        # Reject extraction
        service = ExtractionApprovalService(db, context.user.id, tenant_id)
        try:
            extraction = service.reject_extraction(
                extraction_id,
                request.rejection_reason or "Rejected by user",
            )
            db.commit()
            return ExtractionApprovalResponse(
                extraction_id=extraction.id,
                status=extraction.status,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Approve extraction
    service = ExtractionApprovalService(db, context.user.id, tenant_id)

    try:
        extraction, distribution_summary = service.approve_extraction(
            extraction_id,
            request.approval_notes,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ExtractionApprovalResponse(
        extraction_id=extraction.id,
        status=extraction.status,
        ticket_created_id=extraction.ticket_created_id,
        distributed_at=extraction.distributed_at,
        distribution_summary=distribution_summary,
    )


@router.post(
    "/{extraction_id}/reject",
    response_model=ExtractionApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject extraction",
    description="Reject extraction (do not distribute).",
)
def reject_extraction(
    extraction_id: UUID,
    request: ExtractionApprovalRequest,
    context: RequestContext = Depends(require_permissions("extraction_approve")),
    db: Session = Depends(get_db),
):
    """Reject extraction."""
    tenant_id = context.tenant_id or context.membership.tenant_id
    service = ExtractionApprovalService(db, context.user.id, tenant_id)

    try:
        extraction = service.reject_extraction(
            extraction_id,
            request.rejection_reason or "Rejected by user",
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ExtractionApprovalResponse(
        extraction_id=extraction.id,
        status=extraction.status,
    )


@router.post(
    "/intake/{intake_item_id}/extract",
    response_model=ExtractionTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger OCR extraction",
    description=(
        "Run extraction on an intake item's OCR text, creating a DocumentExtraction record "
        "ready for human review. Pass `force=true` to re-extract an already-processed item."
    ),
)
def trigger_extraction(
    intake_item_id: UUID,
    force: bool = Query(False, description="Re-extract even if a DocumentExtraction already exists"),
    context: RequestContext = Depends(require_permissions("extraction_review")),
    db: Session = Depends(get_db),
):
    """Trigger OCR extraction for an intake item."""
    tenant_id = context.tenant_id or context.membership.tenant_id
    service = OCRExtractionService(db, str(context.user.id), tenant_id)

    was_existing = service.has_existing_extraction(intake_item_id)

    try:
        extraction = service.trigger_extraction_for_intake(intake_item_id, force=force)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Count issues and populated fields
    from sqlalchemy import select as sa_select
    from app.models import ExtractionIssue
    all_issues = list(db.scalars(
        sa_select(ExtractionIssue).where(ExtractionIssue.extraction_id == extraction.id)
    ).all())

    # Count non-empty string fields as "extracted"
    fields_extracted = sum(
        1 for attr in (
            "ticket_number", "driver_name", "truck_number", "material",
            "company_name", "destination", "job_location", "customer_name",
            "ticket_date", "start_time", "finish_time", "weight_net_lbs",
            "tons", "load_count", "invoice_number",
        )
        if getattr(extraction, attr, None)
    )

    return ExtractionTriggerResponse(
        extraction_id=extraction.id,
        intake_item_id=str(intake_item_id),
        status=extraction.status,
        document_type=extraction.document_type,
        issue_count=len(all_issues),
        fields_extracted=fields_extracted,
        is_new=not bool(was_existing) or force,
    )


@router.post(
    "/{extraction_id}/validate",
    response_model=ExtractionDetailResponse,
    summary="Re-run validation",
    description=(
        "Re-run all validation rules against an extraction after corrections have been applied. "
        "Adds any new issues found and returns the updated extraction with its full issue list."
    ),
)
def revalidate_extraction(
    extraction_id: UUID,
    context: RequestContext = Depends(require_permissions("extraction_review")),
    db: Session = Depends(get_db),
):
    """Re-run validation rules after a reviewer has applied corrections."""
    from app.services.extraction_validation import ExtractionValidationService
    from app.models import DocumentExtraction as DE

    tenant_id = context.tenant_id or context.membership.tenant_id

    extraction = db.scalars(
        __import__("sqlalchemy", fromlist=["select"]).select(DE).where(
            DE.id == str(extraction_id),
            DE.tenant_id == tenant_id,
        )
    ).first()

    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    validator = ExtractionValidationService(db, tenant_id)
    validator.validate(extraction)
    db.commit()

    # Return updated detail
    review_service = ExtractionReviewService(db, str(context.user.id), tenant_id)
    issues = review_service.get_extraction_issues(extraction_id)

    extraction_response = DocumentExtractionResponse(
        id=extraction.id,
        tenant_id=extraction.tenant_id,
        intake_item_id=extraction.intake_item_id,
        document_type=extraction.document_type,
        document_type_confidence=float(extraction.document_type_confidence or 0),
        status=extraction.status,
        company_name=extraction.company_name,
        company_name_confidence=float(extraction.company_name_confidence or 0),
        ticket_number=extraction.ticket_number,
        ticket_number_confidence=float(extraction.ticket_number_confidence or 0),
        destination=extraction.destination,
        destination_confidence=float(extraction.destination_confidence or 0),
        material=extraction.material,
        material_confidence=float(extraction.material_confidence or 0),
        tons=extraction.tons,
        invoice_total=extraction.invoice_total,
        review_notes=extraction.review_notes,
        created_at=extraction.created_at,
        created_by=extraction.created_by,
    )
    issues_response = [
        DocumentExtractionIssueResponse(
            id=i.id,
            issue_type=i.issue_type,
            field_name=i.field_name,
            severity=i.severity,
            message=i.message,
            suggested_value=i.suggested_value,
            correction_source=i.correction_source,
            resolved=i.resolved,
            resolved_value=i.resolved_value,
        )
        for i in issues
    ]
    return ExtractionDetailResponse(extraction=extraction_response, issues=issues_response)

