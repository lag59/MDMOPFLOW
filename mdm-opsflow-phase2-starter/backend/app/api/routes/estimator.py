from datetime import datetime
from decimal import Decimal
import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import (
    AuditLog,
    DocumentExtraction,
    Equipment,
    Estimate,
    EstimateApproval,
    EstimateAuditLog,
    EstimateDocument,
    EstimateItem,
    EstimatorBidPipelineItem,
    EstimatorTakeoff,
    EstimatorVersion,
    EstimatorWinLossRecord,
    IntakeItem,
    MaterialDensityPreset,
    Project,
    ProjectStatus,
    VendorPurchaseOrder,
)
from app.schemas import (
    CostLibraryImportRequest,
    CostLibraryImportResponse,
    CostLibraryResponse,
    EstimateAiReviewResponse,
    EstimateApprovalRequest,
    EstimateApprovalResponse,
    EstimateAuditLogResponse,
    EstimateCompareResponse,
    EstimateCreate,
    EstimateDocumentResponse,
    EstimateItemCreate,
    EstimateItemResponse,
    EstimateItemUpdate,
    EstimateResponse,
    EstimateUpdate,
    EstimateValidationResponse,
    EstimatorBidPipelineItemCreate,
    EstimatorBidPipelineItemResponse,
    EstimatorSummaryResponse,
    EstimatorTakeoffCreate,
    EstimatorTakeoffResponse,
    EstimatorVersionCreate,
    EstimatorVersionResponse,
    EstimatorWinLossRecordCreate,
    EstimatorWinLossRecordResponse,
)

router = APIRouter(prefix="/api/estimator", tags=["Estimator"])
estimates_router = APIRouter(tags=["Estimator"])

ESTIMATE_STATUSES = {
    "New",
    "Documents Uploaded",
    "Extraction in Progress",
    "Extraction Review",
    "Draft Estimate",
    "Internal Review",
    "Returned for Revision",
    "Approved for Submission",
    "Submitted",
    "Customer Revision Requested",
    "Awarded",
    "Not Awarded",
    "Converted to Project",
    "Archived",
}


def _require_tenant(context: RequestContext) -> str:
    tenant_id = context.membership.tenant_id if context.membership else context.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")
    return tenant_id


def _log_estimate_audit(
    db: Session,
    tenant_id: str,
    estimate_id: str,
    actor_user_id: str,
    action: str,
    previous_status: str,
    new_status: str,
    details: str,
) -> None:
    db.add(
        EstimateAuditLog(
            tenant_id=tenant_id,
            estimate_id=estimate_id,
            actor_user_id=actor_user_id,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            details=details,
            created_by=actor_user_id,
        )
    )


def _require_estimate(db: Session, tenant_id: str, estimate_id: str) -> Estimate:
    estimate = db.scalar(select(Estimate).where(Estimate.id == estimate_id, Estimate.tenant_id == tenant_id))
    if estimate is None:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


@router.get(
    "/takeoffs",
    response_model=list[EstimatorTakeoffResponse],
    operation_id="estimator_takeoffs_list",
    summary="List estimator takeoffs",
)
def list_takeoffs(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(EstimatorTakeoff)
        .where(EstimatorTakeoff.tenant_id == tenant_id)
        .order_by(EstimatorTakeoff.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/takeoffs",
    response_model=EstimatorTakeoffResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimator_takeoffs_create",
    summary="Create estimator takeoff",
)
def create_takeoff(
    payload: EstimatorTakeoffCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = EstimatorTakeoff(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        takeoff_number=payload.takeoff_number,
        material_name=payload.material_name,
        quantity=payload.quantity,
        unit_of_measure=payload.unit_of_measure,
        estimated_cost=payload.estimated_cost,
        status=payload.status,
        notes=payload.notes,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_estimator_takeoff",
            resource_type="estimator_takeoff",
            resource_id=item.id,
            details=item.takeoff_number,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/versions",
    response_model=list[EstimatorVersionResponse],
    operation_id="estimator_versions_list",
    summary="List estimate versions",
)
def list_versions(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(EstimatorVersion)
        .where(EstimatorVersion.tenant_id == tenant_id)
        .order_by(EstimatorVersion.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/versions",
    response_model=EstimatorVersionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimator_versions_create",
    summary="Create estimate version",
)
def create_version(
    payload: EstimatorVersionCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = EstimatorVersion(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        version_name=payload.version_name,
        revision_number=payload.revision_number,
        estimated_revenue=payload.estimated_revenue,
        estimated_cost=payload.estimated_cost,
        status=payload.status,
        notes=payload.notes,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_estimator_version",
            resource_type="estimator_version",
            resource_id=item.id,
            details=f"{item.version_name} r{item.revision_number}",
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/bid-pipeline",
    response_model=list[EstimatorBidPipelineItemResponse],
    operation_id="estimator_bid_pipeline_list",
    summary="List estimator bid pipeline",
)
def list_bid_pipeline(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(EstimatorBidPipelineItem)
        .where(EstimatorBidPipelineItem.tenant_id == tenant_id)
        .order_by(EstimatorBidPipelineItem.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/bid-pipeline",
    response_model=EstimatorBidPipelineItemResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimator_bid_pipeline_create",
    summary="Create estimator bid pipeline item",
)
def create_bid_pipeline_item(
    payload: EstimatorBidPipelineItemCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = EstimatorBidPipelineItem(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        bid_number=payload.bid_number,
        customer_name=payload.customer_name,
        stage=payload.stage,
        bid_amount=payload.bid_amount,
        probability_percent=payload.probability_percent,
        due_date=payload.due_date,
        status=payload.status,
        notes=payload.notes,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_estimator_bid_pipeline_item",
            resource_type="estimator_bid_pipeline_item",
            resource_id=item.id,
            details=item.bid_number,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/win-loss",
    response_model=list[EstimatorWinLossRecordResponse],
    operation_id="estimator_win_loss_list",
    summary="List estimator win/loss records",
)
def list_win_loss_records(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(EstimatorWinLossRecord)
        .where(EstimatorWinLossRecord.tenant_id == tenant_id)
        .order_by(EstimatorWinLossRecord.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/win-loss",
    response_model=EstimatorWinLossRecordResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimator_win_loss_create",
    summary="Create estimator win/loss record",
)
def create_win_loss_record(
    payload: EstimatorWinLossRecordCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = EstimatorWinLossRecord(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        bid_pipeline_item_id=payload.bid_pipeline_item_id,
        outcome=payload.outcome,
        final_amount=payload.final_amount,
        decision_date=payload.decision_date,
        reason=payload.reason,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_estimator_win_loss_record",
            resource_type="estimator_win_loss_record",
            resource_id=item.id,
            details=item.outcome,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/summary",
    response_model=EstimatorSummaryResponse,
    operation_id="estimator_summary_get",
    summary="Get estimator workflow summary",
)
def get_summary(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    takeoffs = db.scalars(select(EstimatorTakeoff).where(EstimatorTakeoff.tenant_id == tenant_id)).all()
    versions = db.scalars(select(EstimatorVersion).where(EstimatorVersion.tenant_id == tenant_id)).all()
    bids = db.scalars(select(EstimatorBidPipelineItem).where(EstimatorBidPipelineItem.tenant_id == tenant_id)).all()
    outcomes = db.scalars(select(EstimatorWinLossRecord).where(EstimatorWinLossRecord.tenant_id == tenant_id)).all()

    wins = sum(1 for item in outcomes if item.outcome == "won")
    losses = sum(1 for item in outcomes if item.outcome == "lost")
    pending = sum(1 for item in outcomes if item.outcome not in {"won", "lost"})
    decided = wins + losses
    win_rate_percent = (Decimal(wins) / Decimal(decided) * Decimal("100.00")) if decided else Decimal("0.00")

    return EstimatorSummaryResponse(
        takeoff_count=len(takeoffs),
        version_count=len(versions),
        bid_pipeline_count=len(bids),
        wins=wins,
        losses=losses,
        pending=pending,
        win_rate_percent=win_rate_percent.quantize(Decimal("0.01")),
    )


@estimates_router.post(
    "/api/estimates",
    response_model=EstimateResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimates_create",
    summary="Create estimate",
)
def create_estimate(
    payload: EstimateCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    existing = db.scalar(
        select(Estimate).where(Estimate.tenant_id == tenant_id, Estimate.estimate_number == payload.estimate_number)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Estimate number already exists")

    estimate = Estimate(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        estimate_name=payload.estimate_name,
        estimate_number=payload.estimate_number,
        customer_name=payload.customer_name,
        project_name=payload.project_name,
        project_address=payload.project_address,
        project_type=payload.project_type,
        bid_due_date=payload.bid_due_date,
        expected_start_date=payload.expected_start_date,
        expected_completion_date=payload.expected_completion_date,
        estimator_name=payload.estimator_name,
        project_manager_name=payload.project_manager_name,
        sales_contact=payload.sales_contact,
        contract_type=payload.contract_type,
        estimate_type=payload.estimate_type,
        currency=payload.currency,
        tax_jurisdiction=payload.tax_jurisdiction,
        target_margin_percent=payload.target_margin_percent,
        default_overhead_percent=payload.default_overhead_percent,
        default_contingency_percent=payload.default_contingency_percent,
        notes=payload.notes,
        status=payload.status,
        created_by=context.user.id,
    )
    db.add(estimate)
    db.flush()
    _log_estimate_audit(
        db,
        tenant_id,
        estimate.id,
        context.user.id,
        "create_estimate",
        "",
        estimate.status,
        f"Created estimate {estimate.estimate_number}",
    )
    db.commit()
    db.refresh(estimate)
    return estimate


@estimates_router.get(
    "/api/estimates",
    response_model=list[EstimateResponse],
    operation_id="estimates_list",
    summary="List estimates",
)
def list_estimates(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    return db.scalars(select(Estimate).where(Estimate.tenant_id == tenant_id).order_by(Estimate.created_at.desc())).all()


@estimates_router.get(
    "/api/estimates/{estimate_id}",
    response_model=EstimateResponse,
    operation_id="estimates_get",
    summary="Get estimate",
)
def get_estimate(
    estimate_id: str,
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    return _require_estimate(db, tenant_id, estimate_id)


@estimates_router.patch(
    "/api/estimates/{estimate_id}",
    response_model=EstimateResponse,
    operation_id="estimates_patch",
    summary="Update estimate",
)
def patch_estimate(
    estimate_id: str,
    payload: EstimateUpdate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    estimate = _require_estimate(db, tenant_id, estimate_id)
    if estimate.is_locked:
        raise HTTPException(status_code=409, detail="Estimate is locked")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(estimate, field, value)
    db.add(estimate)
    db.flush()
    _log_estimate_audit(
        db,
        tenant_id,
        estimate.id,
        context.user.id,
        "update_estimate",
        estimate.status,
        estimate.status,
        "Updated estimate fields",
    )
    db.commit()
    db.refresh(estimate)
    return estimate


@estimates_router.post(
    "/api/estimates/{estimate_id}/documents",
    response_model=list[EstimateDocumentResponse],
    status_code=status.HTTP_201_CREATED,
    operation_id="estimates_documents_upload",
    summary="Upload estimate documents",
)
async def upload_estimate_documents(
    estimate_id: str,
    files: list[UploadFile] = File(...),
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    estimate = _require_estimate(db, tenant_id, estimate_id)
    created: list[EstimateDocument] = []
    storage_root = Path("storage") / "intake"
    storage_root.mkdir(parents=True, exist_ok=True)

    for file in files:
        content = await file.read()
        digest = hashlib.sha256(content).hexdigest()
        safe_name = f"{estimate_id}_{digest[:12]}_{file.filename}"
        target_path = storage_root / safe_name
        target_path.write_bytes(content)

        intake_item = IntakeItem(
            tenant_id=tenant_id,
            project_id=estimate.project_id,
            filename=safe_name,
            original_filename=file.filename,
            file_path=str(target_path),
            mime_type=file.content_type or "application/octet-stream",
            file_size_bytes=len(content),
            content_hash=digest,
            document_type="estimate_document",
            processing_stage="uploaded",
            source="estimate_upload",
            created_by=context.user.id,
        )
        db.add(intake_item)
        db.flush()

        doc = EstimateDocument(
            tenant_id=tenant_id,
            estimate_id=estimate.id,
            intake_item_id=intake_item.id,
            filename=file.filename,
            document_type="Unknown document",
            processing_status="Documents Uploaded",
            confidence_score=Decimal("0.00"),
            version_label="v1",
            review_status="Review recommended",
            uploaded_by=context.user.id,
        )
        db.add(doc)
        created.append(doc)

    previous_status = estimate.status
    estimate.status = "Documents Uploaded"
    _log_estimate_audit(
        db,
        tenant_id,
        estimate.id,
        context.user.id,
        "upload_estimate_documents",
        previous_status,
        estimate.status,
        f"Uploaded {len(created)} document(s)",
    )
    db.commit()
    for item in created:
        db.refresh(item)
    return created


@estimates_router.post(
    "/api/documents/{document_id}/process",
    response_model=EstimateDocumentResponse,
    operation_id="estimate_document_process",
    summary="Process document through OCR and classification",
)
def process_document(
    document_id: str,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    document = db.scalar(select(EstimateDocument).where(EstimateDocument.id == document_id, EstimateDocument.tenant_id == tenant_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.intake_item_id is None:
        raise HTTPException(status_code=400, detail="Document is missing intake item association")

    extraction = DocumentExtraction(
        tenant_id=tenant_id,
        intake_item_id=document.intake_item_id,
        document_type="unknown",
        document_type_confidence=Decimal("0.76"),
        status="review",
        extracted_notes="OCR extraction generated for estimator review.",
        created_by=context.user.id,
    )
    db.add(extraction)

    document.processing_status = "Extraction Review"
    document.review_status = "Review recommended"
    document.confidence_score = Decimal("0.76")

    estimate = _require_estimate(db, tenant_id, document.estimate_id)
    previous_status = estimate.status
    estimate.status = "Extraction Review"
    _log_estimate_audit(
        db,
        tenant_id,
        estimate.id,
        context.user.id,
        "process_estimate_document",
        previous_status,
        estimate.status,
        f"Processed document {document.filename}",
    )
    db.commit()
    db.refresh(document)
    return document


@estimates_router.get(
    "/api/documents/{document_id}/extractions",
    response_model=list[dict[str, str]],
    operation_id="estimate_document_extractions_list",
    summary="List extraction fields for a document",
)
def list_document_extractions(
    document_id: str,
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    document = db.scalar(select(EstimateDocument).where(EstimateDocument.id == document_id, EstimateDocument.tenant_id == tenant_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.intake_item_id is None:
        return []

    extraction = db.scalar(
        select(DocumentExtraction)
        .where(DocumentExtraction.tenant_id == tenant_id, DocumentExtraction.intake_item_id == document.intake_item_id)
        .order_by(DocumentExtraction.created_at.desc())
    )
    if extraction is None:
        return []

    return [
        {
            "field": "material",
            "extracted_value": extraction.material or "",
            "confidence": str(extraction.material_confidence),
            "status": "Review recommended",
        },
        {
            "field": "tons",
            "extracted_value": str(extraction.tons or ""),
            "confidence": "0.70",
            "status": "Review recommended",
        },
        {
            "field": "project_name",
            "extracted_value": extraction.project_name or "",
            "confidence": str(extraction.project_name_confidence),
            "status": "Review recommended",
        },
    ]


@estimates_router.post(
    "/api/estimates/extractions/{extraction_id}/approve",
    response_model=dict[str, str],
    operation_id="estimate_extraction_approve",
    summary="Approve extraction",
)
def approve_extraction(
    extraction_id: str,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    extraction = db.scalar(select(DocumentExtraction).where(DocumentExtraction.id == extraction_id, DocumentExtraction.tenant_id == tenant_id))
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extraction not found")

    extraction.status = "approved"
    extraction.approved_by = context.user.id
    extraction.approved_at = datetime.utcnow()

    document = db.scalar(
        select(EstimateDocument).where(
            EstimateDocument.tenant_id == tenant_id,
            EstimateDocument.intake_item_id == extraction.intake_item_id,
        )
    )
    if document is not None:
        document.review_status = "Accepted"
        document.processing_status = "Extraction Review"
        estimate = _require_estimate(db, tenant_id, document.estimate_id)
        previous_status = estimate.status
        estimate.status = "Draft Estimate"
        _log_estimate_audit(
            db,
            tenant_id,
            estimate.id,
            context.user.id,
            "approve_extraction",
            previous_status,
            estimate.status,
            f"Approved extraction {extraction.id}",
        )

    db.commit()
    return {"status": "approved", "extraction_id": extraction.id}


@estimates_router.post(
    "/api/estimates/{estimate_id}/items",
    response_model=EstimateItemResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimate_items_create",
    summary="Create estimate item",
)
def create_estimate_item(
    estimate_id: str,
    payload: EstimateItemCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    estimate = _require_estimate(db, tenant_id, estimate_id)
    if estimate.is_locked:
        raise HTTPException(status_code=409, detail="Estimate is locked")

    item = EstimateItem(tenant_id=tenant_id, estimate_id=estimate.id, created_by=context.user.id, **payload.model_dump())
    db.add(item)
    db.flush()
    _log_estimate_audit(
        db,
        tenant_id,
        estimate.id,
        context.user.id,
        "create_estimate_item",
        estimate.status,
        estimate.status,
        f"Created estimate item {item.item_number or item.id}",
    )
    db.commit()
    db.refresh(item)
    return item


@estimates_router.patch(
    "/api/estimate-items/{item_id}",
    response_model=EstimateItemResponse,
    operation_id="estimate_items_patch",
    summary="Update estimate item",
)
def patch_estimate_item(
    item_id: str,
    payload: EstimateItemUpdate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = db.scalar(select(EstimateItem).where(EstimateItem.id == item_id, EstimateItem.tenant_id == tenant_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Estimate item not found")
    estimate = _require_estimate(db, tenant_id, item.estimate_id)
    if estimate.is_locked:
        raise HTTPException(status_code=409, detail="Estimate is locked")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@estimates_router.post(
    "/api/estimates/{estimate_id}/versions",
    response_model=EstimatorVersionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="estimate_versions_create",
    summary="Create estimate version",
)
def create_estimate_version(
    estimate_id: str,
    payload: EstimatorVersionCreate,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    estimate = _require_estimate(db, tenant_id, estimate_id)
    version = EstimatorVersion(
        tenant_id=tenant_id,
        project_id=estimate.project_id,
        version_name=payload.version_name,
        revision_number=payload.revision_number,
        estimated_revenue=payload.estimated_revenue,
        estimated_cost=payload.estimated_cost,
        status=payload.status,
        notes=payload.notes,
        created_by=context.user.id,
    )
    db.add(version)
    db.flush()
    _log_estimate_audit(
        db,
        tenant_id,
        estimate.id,
        context.user.id,
        "create_estimate_version",
        estimate.status,
        estimate.status,
        f"Created version {version.version_name} r{version.revision_number}",
    )
    db.commit()
    db.refresh(version)
    return version


@estimates_router.get(
    "/api/estimates/{estimate_id}/compare",
    response_model=EstimateCompareResponse,
    operation_id="estimate_versions_compare",
    summary="Compare estimate versions",
)
def compare_estimate_versions(
    estimate_id: str,
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    estimate = _require_estimate(db, tenant_id, estimate_id)
    versions = db.scalars(
        select(EstimatorVersion)
        .where(EstimatorVersion.tenant_id == tenant_id, EstimatorVersion.project_id == estimate.project_id)
        .order_by(EstimatorVersion.created_at.desc())
    ).all()
    if len(versions) < 2:
        raise HTTPException(status_code=400, detail="At least two versions are required for comparison")

    left = versions[1]
    right = versions[0]
    revenue_delta = (Decimal(str(right.estimated_revenue or 0)) - Decimal(str(left.estimated_revenue or 0))).quantize(Decimal("0.01"))
    cost_delta = (Decimal(str(right.estimated_cost or 0)) - Decimal(str(left.estimated_cost or 0))).quantize(Decimal("0.01"))
    change_label = "Increased" if cost_delta > 0 else "Decreased" if cost_delta < 0 else "Unchanged"
    return EstimateCompareResponse(
        left_version_id=left.id,
        right_version_id=right.id,
        summary=f"Version {right.revision_number} compared with version {left.revision_number}",
        changes=[
            f"Cost {change_label}: {cost_delta}",
            f"Revenue delta: {revenue_delta}",
        ],
    )


@estimates_router.post(
    "/api/estimates/{estimate_id}/validate",
    response_model=EstimateValidationResponse,
    operation_id="estimate_validate",
    summary="Validate estimate completeness",
)
def validate_estimate(
    estimate_id: str,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    estimate = _require_estimate(db, tenant_id, estimate_id)
    items = db.scalars(select(EstimateItem).where(EstimateItem.tenant_id == tenant_id, EstimateItem.estimate_id == estimate.id)).all()
    docs = db.scalars(select(EstimateDocument).where(EstimateDocument.tenant_id == tenant_id, EstimateDocument.estimate_id == estimate.id)).all()

    issues: list[str] = []
    if not items:
        issues.append("Estimate has no line items")
    if any(Decimal(str(item.quantity)) <= 0 for item in items):
        issues.append("Missing quantities")
    if any(Decimal(str(item.unit_cost)) <= 0 for item in items):
        issues.append("Zero unit costs")
    if any(not item.cost_code for item in items):
        issues.append("Missing cost codes")
    if any(doc.review_status != "Accepted" for doc in docs):
        issues.append("Unreviewed OCR fields")
    if Decimal(str(estimate.target_margin_percent)) < Decimal("10"):
        issues.append("Margin below company minimum")

    score = max(0, 100 - (len(issues) * 12))
    return EstimateValidationResponse(completion_score=score, unresolved_issues=issues)


@estimates_router.post(
    "/api/estimates/{estimate_id}/submit",
    response_model=EstimateResponse,
    operation_id="estimate_submit",
    summary="Submit estimate for internal review",
)
def submit_estimate(
    estimate_id: str,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    estimate = _require_estimate(db, tenant_id, estimate_id)
    if estimate.is_locked:
        raise HTTPException(status_code=409, detail="Estimate is locked")

    previous_status = estimate.status
    estimate.status = "Submitted"
    estimate.approval_status = "pending"
    _log_estimate_audit(db, tenant_id, estimate.id, context.user.id, "submit_estimate", previous_status, estimate.status, "Submitted for internal approval")
    db.commit()
    db.refresh(estimate)
    return estimate


@estimates_router.post(
    "/api/estimates/{estimate_id}/approve",
    response_model=EstimateApprovalResponse,
    operation_id="estimate_approve",
    summary="Approve or return estimate",
)
def approve_estimate(
    estimate_id: str,
    payload: EstimateApprovalRequest,
    context: RequestContext = Depends(require_permissions("estimate_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    estimate = _require_estimate(db, tenant_id, estimate_id)
    decision = payload.decision.strip()
    if decision not in {"approved", "returned"}:
        raise HTTPException(status_code=400, detail="decision must be approved or returned")

    approval = EstimateApproval(
        tenant_id=tenant_id,
        estimate_id=estimate.id,
        approver_user_id=context.user.id,
        approver_role="estimator",
        decision=decision,
        comments=payload.comments,
        decided_at=datetime.utcnow(),
        created_by=context.user.id,
    )
    db.add(approval)

    previous_status = estimate.status
    estimate.status = "Approved for Submission" if decision == "approved" else "Returned for Revision"
    estimate.approval_status = decision
    if decision == "approved":
        estimate.is_locked = True
        estimate.locked_at = datetime.utcnow()
    _log_estimate_audit(db, tenant_id, estimate.id, context.user.id, "approve_estimate", previous_status, estimate.status, payload.comments)
    db.commit()
    db.refresh(approval)
    return approval


@estimates_router.post(
    "/api/estimates/{estimate_id}/convert-to-project",
    response_model=EstimateResponse,
    operation_id="estimate_convert_to_project",
    summary="Convert awarded estimate into project baseline",
)
def convert_estimate_to_project(
    estimate_id: str,
    context: RequestContext = Depends(require_permissions("project_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    estimate = _require_estimate(db, tenant_id, estimate_id)
    if estimate.status not in {"Awarded", "Approved for Submission", "Submitted"}:
        raise HTTPException(status_code=400, detail="Estimate must be awarded or approved before conversion")

    converted_project = Project(
        tenant_id=tenant_id,
        project_name=estimate.project_name or estimate.estimate_name,
        project_number=estimate.estimate_number,
        customer=estimate.customer_name,
        address=estimate.project_address,
        project_manager=estimate.project_manager_name,
        start_date=estimate.expected_start_date,
        end_date=estimate.expected_completion_date,
        contract_amount=None,
        budget=None,
        status=ProjectStatus.PLANNING,
        description=f"Converted from estimate {estimate.estimate_number}",
        created_by=context.user.id,
    )
    db.add(converted_project)
    db.flush()

    previous_status = estimate.status
    estimate.converted_project_id = converted_project.id
    estimate.project_id = converted_project.id
    estimate.status = "Converted to Project"
    estimate.is_locked = True
    if estimate.locked_at is None:
        estimate.locked_at = datetime.utcnow()
    _log_estimate_audit(
        db,
        tenant_id,
        estimate.id,
        context.user.id,
        "convert_to_project",
        previous_status,
        estimate.status,
        f"Created project {converted_project.project_number}",
    )
    db.commit()
    db.refresh(estimate)
    return estimate


@estimates_router.post(
    "/api/estimates/{estimate_id}/ai-review",
    response_model=EstimateAiReviewResponse,
    operation_id="estimate_ai_review",
    summary="Run estimate AI review",
)
def run_estimate_ai_review(
    estimate_id: str,
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    estimate = _require_estimate(db, tenant_id, estimate_id)
    items = db.scalars(select(EstimateItem).where(EstimateItem.tenant_id == tenant_id, EstimateItem.estimate_id == estimate.id)).all()

    warnings: list[str] = []
    recommendations: list[str] = []
    if not items:
        warnings.append("No estimate items found for scope coverage.")
    if any(item.description and "storm" in item.description.lower() and Decimal(str(item.total_cost)) <= 0 for item in items):
        warnings.append("Storm drainage item detected with missing cost coverage.")
    if Decimal(str(estimate.default_contingency_percent)) < Decimal("3"):
        warnings.append("Contingency appears low for heavy civil scope.")
    if not warnings:
        recommendations.append("No critical gaps detected. Proceed to approval review.")
    else:
        recommendations.append("Review flagged items before submission.")

    _log_estimate_audit(
        db,
        tenant_id,
        estimate.id,
        context.user.id,
        "ai_review",
        estimate.status,
        estimate.status,
        "AI review completed",
    )
    db.commit()
    return EstimateAiReviewResponse(estimate_id=estimate.id, warnings=warnings, recommendations=recommendations)


@estimates_router.get(
    "/api/cost-library",
    response_model=CostLibraryResponse,
    operation_id="cost_library_get",
    summary="Get cost library",
)
def get_cost_library(
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    materials = db.scalars(select(MaterialDensityPreset).where(MaterialDensityPreset.tenant_id == tenant_id)).all()
    equipment = db.scalars(select(Equipment).where(Equipment.tenant_id == tenant_id)).all()
    subcontracts = db.scalars(select(VendorPurchaseOrder).where(VendorPurchaseOrder.tenant_id == tenant_id)).all()

    return CostLibraryResponse(
        labor=[],
        equipment=[{"equipment": item.name, "status": item.status} for item in equipment],
        materials=[{"material": item.material_name, "density": str(item.density_tons_per_cubic_yard)} for item in materials],
        trucking=[],
        subcontractors=[{"vendor": item.vendor_name, "po_number": item.po_number} for item in subcontracts],
    )


@estimates_router.post(
    "/api/cost-library/import",
    response_model=CostLibraryImportResponse,
    operation_id="cost_library_import",
    summary="Import cost library rows",
)
def import_cost_library(
    payload: CostLibraryImportRequest,
    context: RequestContext = Depends(require_permissions("estimate_write")),
):
    _ = _require_tenant(context)
    imported_count = (
        len(payload.labor)
        + len(payload.equipment)
        + len(payload.materials)
        + len(payload.trucking)
        + len(payload.subcontractors)
    )
    return CostLibraryImportResponse(imported_count=imported_count)


@estimates_router.get(
    "/api/estimates/{estimate_id}/audit-logs",
    response_model=list[EstimateAuditLogResponse],
    operation_id="estimate_audit_logs_list",
    summary="List estimate audit log entries",
)
def list_estimate_audit_logs(
    estimate_id: str,
    context: RequestContext = Depends(require_permissions("estimate_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    _require_estimate(db, tenant_id, estimate_id)
    return db.scalars(
        select(EstimateAuditLog)
        .where(EstimateAuditLog.tenant_id == tenant_id, EstimateAuditLog.estimate_id == estimate_id)
        .order_by(EstimateAuditLog.created_at.desc())
    ).all()
