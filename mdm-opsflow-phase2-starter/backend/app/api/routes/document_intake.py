from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions, resolve_tenant_scope
from app.models import AuditLog
from app.schemas import DocumentIntakeConfigResponse, DocumentIntakeProjectResponse, DocumentIntakeRouteResponse, DocumentIntakeVendorResponse
from app.services.document_intake_router import (
    AUTO_POST_FINANCIAL_OR_TICKET_MIN_CONFIDENCE,
    AUTO_ROUTE_MIN_CONFIDENCE,
    DOCUMENT_RULES,
    UNKNOWN_ROUTE,
    route_ocr_document,
)
from app.services.intake_processing import extract_document_text


router = APIRouter(prefix="/api/document-intake", tags=["Document Intake"])


def _routes_config() -> dict[str, str]:
    routes = {document_type: route for document_type, (_, route, _) in DOCUMENT_RULES.items()}
    routes["unknown"] = UNKNOWN_ROUTE
    return routes


@router.get(
    "/config",
    response_model=DocumentIntakeConfigResponse,
    operation_id="document_intake_config_get",
    summary="Get document intake routing config",
    description="Returns confidence gates and supported document routing destinations for OCR document intake.",
)
def get_document_intake_config(
    context: RequestContext = Depends(require_permissions("intake_read")),
) -> DocumentIntakeConfigResponse:
    _ = resolve_tenant_scope(context)
    return DocumentIntakeConfigResponse(
        auto_route_min_confidence=AUTO_ROUTE_MIN_CONFIDENCE,
        auto_post_financial_or_ticket_min_confidence=AUTO_POST_FINANCIAL_OR_TICKET_MIN_CONFIDENCE,
        never_silent_overwrite=True,
        preserve_source_value=True,
        preserve_units=True,
        flag_cross_document_conflicts=True,
        require_tenant_scope=True,
        create_audit_event=True,
        routes=_routes_config(),
    )


@router.post(
    "",
    response_model=DocumentIntakeRouteResponse,
    status_code=status.HTTP_200_OK,
    operation_id="document_intake_route_upload",
    summary="Classify and route an uploaded document",
    description=(
        "Extracts OCR text from an uploaded PDF, image, or text file, classifies the document, "
        "extracts supported facts only, and returns strict routing JSON for review/import screens."
    ),
)
async def route_uploaded_document(
    file: UploadFile = File(...),
    context: RequestContext = Depends(require_permissions("intake_write")),
    db: Session = Depends(get_db),
) -> DocumentIntakeRouteResponse:
    tenant_id = resolve_tenant_scope(context)
    payload = await file.read()
    raw_text = extract_document_text(payload, file.content_type or "application/octet-stream")
    result = route_ocr_document(raw_text)

    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="document_intake_route_preview",
            resource_type="document_intake",
            resource_id=file.filename or "upload",
            details=f"document_type={result.document_type}; route={result.recommended_route}; confidence={result.classification_confidence}",
            created_by=context.user.id,
        )
    )
    db.commit()

    return DocumentIntakeRouteResponse(
        document_type=result.document_type,
        classification_confidence=result.classification_confidence,
        recommended_route=result.recommended_route,
        project=DocumentIntakeProjectResponse(**result.project),
        vendor=DocumentIntakeVendorResponse(**result.vendor),
        extracted_fields=result.extracted_fields,
        uncertain_fields=result.uncertain_fields,
        conflicts=result.conflicts,
        requires_human_review=result.requires_human_review,
        reason_for_review=result.reason_for_review,
    )