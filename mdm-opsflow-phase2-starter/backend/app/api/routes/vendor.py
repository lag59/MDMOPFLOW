from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions
from app.models import (
    AuditLog,
    VendorComplianceDocument,
    VendorDeliveryRecord,
    VendorInvoiceSubmission,
    VendorPurchaseOrder,
)
from app.schemas import (
    VendorComplianceDocumentCreate,
    VendorComplianceDocumentResponse,
    VendorDeliveryRecordCreate,
    VendorDeliveryRecordResponse,
    VendorInvoiceSubmissionCreate,
    VendorInvoiceSubmissionResponse,
    VendorPurchaseOrderCreate,
    VendorPurchaseOrderResponse,
)

router = APIRouter(prefix="/api/vendor", tags=["Vendor Portal"])


def _require_tenant(context: RequestContext) -> str:
    tenant_id = context.membership.tenant_id if context.membership else context.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID is required")
    return tenant_id


@router.get(
    "/purchase-orders",
    response_model=list[VendorPurchaseOrderResponse],
    operation_id="vendor_purchase_orders_list",
    summary="List vendor purchase orders",
)
def list_purchase_orders(
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(VendorPurchaseOrder)
        .where(VendorPurchaseOrder.tenant_id == tenant_id)
        .order_by(VendorPurchaseOrder.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/purchase-orders",
    response_model=VendorPurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="vendor_purchase_orders_create",
    summary="Create vendor purchase order",
)
def create_purchase_order(
    payload: VendorPurchaseOrderCreate,
    context: RequestContext = Depends(require_permissions("portal_vendor_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = VendorPurchaseOrder(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        po_number=payload.po_number,
        vendor_name=payload.vendor_name,
        description=payload.description,
        status=payload.status,
        total_amount=payload.total_amount,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_vendor_purchase_order",
            resource_type="vendor_purchase_order",
            resource_id=item.id,
            details=item.po_number,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/invoice-submissions",
    response_model=list[VendorInvoiceSubmissionResponse],
    operation_id="vendor_invoice_submissions_list",
    summary="List vendor invoice submissions",
)
def list_invoice_submissions(
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(VendorInvoiceSubmission)
        .where(VendorInvoiceSubmission.tenant_id == tenant_id)
        .order_by(VendorInvoiceSubmission.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/invoice-submissions",
    response_model=VendorInvoiceSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="vendor_invoice_submissions_create",
    summary="Create vendor invoice submission",
)
def create_invoice_submission(
    payload: VendorInvoiceSubmissionCreate,
    context: RequestContext = Depends(require_permissions("portal_vendor_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = VendorInvoiceSubmission(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        purchase_order_id=payload.purchase_order_id,
        invoice_number=payload.invoice_number,
        vendor_name=payload.vendor_name,
        amount=payload.amount,
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
            action="create_vendor_invoice_submission",
            resource_type="vendor_invoice_submission",
            resource_id=item.id,
            details=item.invoice_number,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/delivery-records",
    response_model=list[VendorDeliveryRecordResponse],
    operation_id="vendor_delivery_records_list",
    summary="List vendor delivery records",
)
def list_delivery_records(
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(VendorDeliveryRecord)
        .where(VendorDeliveryRecord.tenant_id == tenant_id)
        .order_by(VendorDeliveryRecord.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/delivery-records",
    response_model=VendorDeliveryRecordResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="vendor_delivery_records_create",
    summary="Create vendor delivery record",
)
def create_delivery_record(
    payload: VendorDeliveryRecordCreate,
    context: RequestContext = Depends(require_permissions("portal_vendor_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = VendorDeliveryRecord(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        purchase_order_id=payload.purchase_order_id,
        ticket_number=payload.ticket_number,
        vendor_name=payload.vendor_name,
        destination=payload.destination,
        status=payload.status,
        received_at=payload.received_at,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_vendor_delivery_record",
            resource_type="vendor_delivery_record",
            resource_id=item.id,
            details=item.ticket_number,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/compliance-documents",
    response_model=list[VendorComplianceDocumentResponse],
    operation_id="vendor_compliance_documents_list",
    summary="List vendor compliance documents",
)
def list_compliance_documents(
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    query = (
        select(VendorComplianceDocument)
        .where(VendorComplianceDocument.tenant_id == tenant_id)
        .order_by(VendorComplianceDocument.created_at.desc())
    )
    return db.scalars(query).all()


@router.post(
    "/compliance-documents",
    response_model=VendorComplianceDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="vendor_compliance_documents_create",
    summary="Create vendor compliance document",
)
def create_compliance_document(
    payload: VendorComplianceDocumentCreate,
    context: RequestContext = Depends(require_permissions("portal_vendor_write")),
    db: Session = Depends(get_db),
):
    tenant_id = _require_tenant(context)
    item = VendorComplianceDocument(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        document_name=payload.document_name,
        vendor_name=payload.vendor_name,
        status=payload.status,
        expires_at=payload.expires_at,
        notes=payload.notes,
        created_by=context.user.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=context.user.id,
            action="create_vendor_compliance_document",
            resource_type="vendor_compliance_document",
            resource_id=item.id,
            details=item.document_name,
            created_by=context.user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item
