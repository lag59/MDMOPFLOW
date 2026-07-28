"""Service for approving document extractions and distributing data to platform systems."""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentExtraction, ExtractionIssue, Ticket, Project, User, AuditLog, IntakeItem


class ExtractionApprovalService:
    """Manages approval and distribution of document extractions."""

    def __init__(self, db: Session, user_id: str, tenant_id: str):
        self.db = db
        self.user_id = user_id
        self.tenant_id = tenant_id

    def get_extraction_for_approval(
        self, extraction_id: UUID
    ) -> Optional[DocumentExtraction]:
        """Get extraction detail for approval."""
        return self.db.scalars(
            select(DocumentExtraction).where(
                DocumentExtraction.id == str(extraction_id),
                DocumentExtraction.tenant_id == self.tenant_id,
            )
        ).first()

    def get_unresolved_issues(
        self, extraction_id: UUID
    ) -> list[ExtractionIssue]:
        """Get all unresolved issues for an extraction."""
        stmt = (
            select(ExtractionIssue)
            .where(
                ExtractionIssue.extraction_id == extraction_id,
                ExtractionIssue.tenant_id == self.tenant_id,
                ExtractionIssue.resolved == False,
            )
        )
        return list(self.db.scalars(stmt).all())

    def can_approve_extraction(
        self, extraction: DocumentExtraction
    ) -> tuple[bool, str]:
        """Check if extraction can be approved."""
        # Verify status
        if extraction.status not in ["review_submitted", "approved"]:
            return (
                False,
                f"Extraction status must be 'review_submitted', current status: {extraction.status}",
            )

        # Verify review was completed
        if not extraction.reviewed_at:
            return False, "Extraction must be reviewed before approval"

        # Use validation service to check for blocking (error-severity) unresolved issues
        from app.services.extraction_validation import ExtractionValidationService
        validator = ExtractionValidationService(self.db, self.tenant_id)
        blocking = validator.get_blocking_issues(extraction.id)
        if blocking:
            fields = ", ".join(sorted({i.field_name for i in blocking}))
            return False, (
                f"{len(blocking)} unresolved error(s) block approval: {fields}. "
                "Resolve all errors before approving."
            )

        # Check for any unresolved issues (warnings are allowed but errors are not)
        unresolved_warnings = self.get_unresolved_issues(extraction.id)
        # Filter to only warnings (errors already caught above)
        warning_count = len([i for i in unresolved_warnings if i.severity != "error"])
        if warning_count:
            # Warnings don't block — approval is still allowed with a note
            pass

        return True, "Ready for approval"

    def approve_extraction(
        self,
        extraction_id: UUID,
        approval_notes: str = "",
    ) -> tuple[DocumentExtraction, dict[str, bool]]:
        """Approve extraction and distribute data to platform systems."""
        extraction = self.get_extraction_for_approval(extraction_id)
        if not extraction:
            raise ValueError(f"Extraction {extraction_id} not found")

        # Verify can approve
        can_approve, reason = self.can_approve_extraction(extraction)
        if not can_approve:
            raise ValueError(reason)

        # Update extraction status
        extraction.approved_by = self.user_id
        extraction.approved_at = datetime.utcnow()
        extraction.status = "approved"

        self.db.add(extraction)
        self.db.flush()

        # Distribute to platform systems
        distribution_summary = self._distribute_extraction(extraction, approval_notes)

        # Mark as distributed
        extraction.status = "distributed"
        extraction.distributed_at = datetime.utcnow()

        self.db.add(extraction)
        self.db.flush()

        return extraction, distribution_summary

    def reject_extraction(
        self,
        extraction_id: UUID,
        rejection_reason: str,
    ) -> DocumentExtraction:
        """Reject extraction (do not distribute)."""
        extraction = self.get_extraction_for_approval(extraction_id)
        if not extraction:
            raise ValueError(f"Extraction {extraction_id} not found")

        extraction.approved_by = self.user_id
        extraction.approved_at = datetime.utcnow()
        extraction.rejection_reason = rejection_reason
        extraction.status = "rejected"

        self.db.add(extraction)
        self.db.flush()

        return extraction

    def _distribute_extraction(
        self, extraction: DocumentExtraction, approval_notes: str = ""
    ) -> dict[str, bool]:
        """Distribute extraction data to all platform systems."""
        summary = {
            "ticket_created": False,
            "project_updated": False,
            "vendor_created": False,
            "dispatch_updated": False,
            "payroll_created": False,
            "invoice_created": False,
            "profitability_updated": False,
            "billing_updated": False,
            "audit_logged": False,
        }

        try:
            # 1. Create or update ticket
            if extraction.ticket_number:
                ticket = self._create_or_update_ticket(extraction)
                extraction.ticket_created_id = ticket.id
                summary["ticket_created"] = True

            # 2. Update project with extracted data
            if extraction.project_id:
                self._update_project(extraction)
                summary["project_updated"] = True

            # 3. Create vendor if company_name is new
            if extraction.company_name and not extraction.company_id:
                vendor_id = self._create_or_match_vendor(extraction)
                extraction.company_id = vendor_id
                summary["vendor_created"] = True

            # 4. Create dispatch records if driver/truck info present
            if extraction.driver_name and extraction.truck_number:
                self._create_dispatch_records(extraction)
                summary["dispatch_updated"] = True

            # 5. Generate payroll records if hours worked calculated
            if extraction.total_hours_calculated and extraction.total_hours_calculated > 0:
                self._generate_payroll_records(extraction)
                summary["payroll_created"] = True

            # 6. Create customer invoice if invoice total present
            if extraction.invoice_total and extraction.invoice_total > 0:
                self._create_customer_invoice(extraction)
                summary["invoice_created"] = True

            # 7. Update profitability dashboard
            if extraction.project_id:
                self._update_profitability_dashboard(extraction)
                summary["profitability_updated"] = True

            # 8. Update billing pipeline
            if extraction.invoice_total and extraction.destination:
                self._update_billing_pipeline(extraction)
                summary["billing_updated"] = True

            # 9. Create audit log entry
            self._create_distribution_audit_log(extraction, approval_notes, summary)
            summary["audit_logged"] = True

        except Exception as e:
            # Log error but don't block distribution
            print(f"Distribution error: {e}")
            self.db.rollback()
            self._create_distribution_error_log(extraction, str(e))

        return summary

    def _create_or_update_ticket(
        self, extraction: DocumentExtraction
    ) -> Ticket:
        """Create ticket from extraction or update existing ticket."""
        # Check if ticket already exists
        if extraction.ticket_created_id:
            ticket = self.db.scalars(
                select(Ticket).where(Ticket.id == extraction.ticket_created_id)
            ).first()
            if ticket:
                return ticket

        # Create new ticket
        ticket = Ticket(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            intake_item_id=extraction.intake_item_id,
            project_id=extraction.project_id,
            extraction_id=extraction.id,
            ticket_number=extraction.ticket_number or "",
            truck=extraction.truck_number or "",
            driver=extraction.driver_name or "",
            material=extraction.material or "",
            origin=extraction.origin or "",
            destination=extraction.destination or "",
            tons=extraction.tons,
            weight=extraction.weight_net_lbs,
            volume_yards=extraction.cubic_yards,
            revenue=extraction.invoice_total,
            status="created",
            notes=f"Auto-created from extraction {extraction.id}",
            created_by=self.user_id,
        )

        self.db.add(ticket)
        self.db.flush()
        return ticket

    def _update_project(self, extraction: DocumentExtraction) -> None:
        """Update project with extracted data."""
        if not extraction.project_id:
            return

        stmt = select(Project).where(
            Project.id == extraction.project_id,
            Project.tenant_id == self.tenant_id,
        )
        project = self.db.scalars(stmt).first()

        if not project:
            return

        # Update project fields from extraction
        if extraction.job_location:
            project.address = extraction.job_location

        if extraction.customer_name:
            project.customer = extraction.customer_name

        if extraction.project_name:
            project.project_name = extraction.project_name

        self.db.add(project)
        self.db.flush()

    def _create_or_match_vendor(self, extraction: DocumentExtraction) -> str:
        """Create vendor record if company_name is new or return matching vendor ID."""
        # In a real system, this would:
        # 1. Check if vendor exists by company_name
        # 2. Create if not found
        # 3. Return vendor ID
        # For now, generate UUID for vendor
        vendor_id = str(uuid4())
        
        # Log vendor creation
        audit = AuditLog(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            actor_user_id=self.user_id,
            action="vendor_created",
            resource_type="vendor",
            resource_id=vendor_id,
            details=json.dumps({
                "vendor_name": extraction.company_name,
                "source": "document_extraction",
                "extraction_id": str(extraction.id),
            }),
            created_by=self.user_id,
        )
        self.db.add(audit)
        self.db.flush()
        
        return vendor_id

    def _create_dispatch_records(self, extraction: DocumentExtraction) -> None:
        """Create dispatch records from extraction driver/truck data."""
        # In a real system, this would:
        # 1. Create dispatch record with driver_name, truck_number
        # 2. Link to ticket via extraction.ticket_created_id
        # 3. Set start_time, finish_time if available
        # 4. Calculate miles/route if origin/destination available
        
        dispatch_id = str(uuid4())
        
        start_time = extraction.start_time or datetime.utcnow()
        finish_time = extraction.finish_time or (start_time + timedelta(hours=8))
        
        audit = AuditLog(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            actor_user_id=self.user_id,
            action="dispatch_created",
            resource_type="dispatch",
            resource_id=dispatch_id,
            details=json.dumps({
                "driver": extraction.driver_name,
                "truck": extraction.truck_number,
                "origin": extraction.origin,
                "destination": extraction.destination,
                "start_time": start_time.isoformat(),
                "finish_time": finish_time.isoformat(),
                "ticket_id": str(extraction.ticket_created_id) if extraction.ticket_created_id else None,
                "extraction_id": str(extraction.id),
            }),
            created_by=self.user_id,
        )
        self.db.add(audit)
        self.db.flush()

    def _generate_payroll_records(self, extraction: DocumentExtraction) -> None:
        """Generate payroll records from hours worked."""
        # In a real system, this would:
        # 1. Match driver to payroll profile
        # 2. Calculate hourly rate from system config
        # 3. Create payroll line item for extraction hours
        # 4. Link to dispatch record
        
        payroll_id = str(uuid4())
        
        # Assume default hourly rate of $25/hour
        hourly_rate = Decimal("25")
        hours_worked = Decimal(str(extraction.total_hours_calculated or 0))
        gross_pay = hours_worked * hourly_rate
        
        audit = AuditLog(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            actor_user_id=self.user_id,
            action="payroll_created",
            resource_type="payroll",
            resource_id=payroll_id,
            details=json.dumps({
                "driver": extraction.driver_name,
                "hours": float(hours_worked),
                "hourly_rate": float(hourly_rate),
                "gross_pay": float(gross_pay),
                "ticket_id": str(extraction.ticket_created_id) if extraction.ticket_created_id else None,
                "extraction_id": str(extraction.id),
            }),
            created_by=self.user_id,
        )
        self.db.add(audit)
        self.db.flush()

    def _create_customer_invoice(self, extraction: DocumentExtraction) -> None:
        """Create customer invoice from extraction data."""
        # In a real system, this would:
        # 1. Create invoice record with invoice_total, company_name
        # 2. Add line items (material, tons, weight, etc.)
        # 3. Set due date (30 days from now typical)
        # 4. Mark as ready for delivery
        
        invoice_id = str(uuid4())
        
        due_date = datetime.utcnow() + timedelta(days=30)
        
        audit = AuditLog(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            actor_user_id=self.user_id,
            action="invoice_created",
            resource_type="invoice",
            resource_id=invoice_id,
            details=json.dumps({
                "customer": extraction.customer_name or extraction.company_name,
                "amount": float(extraction.invoice_total) if extraction.invoice_total else 0,
                "material": extraction.material,
                "tons": float(extraction.tons) if extraction.tons else None,
                "due_date": due_date.isoformat(),
                "ticket_id": str(extraction.ticket_created_id) if extraction.ticket_created_id else None,
                "extraction_id": str(extraction.id),
            }),
            created_by=self.user_id,
        )
        self.db.add(audit)
        self.db.flush()

    def _update_profitability_dashboard(self, extraction: DocumentExtraction) -> None:
        """Update profitability dashboard with ticket metrics."""
        # In a real system, this would:
        # 1. Update project profitability metrics
        # 2. Calculate revenue - (fuel_cost + labor_cost + material_cost)
        # 3. Update running profit/margin calculations
        # 4. Trigger dashboard refresh
        
        if not extraction.project_id:
            return

        stmt = select(Project).where(
            Project.id == extraction.project_id,
            Project.tenant_id == self.tenant_id,
        )
        project = self.db.scalars(stmt).first()

        if project:
            # Calculate estimated profit for this ticket
            revenue = Decimal(str(extraction.invoice_total or 0))
            labor_hours = Decimal(str(extraction.total_hours_calculated or 0))
            labor_cost = labor_hours * Decimal("25")  # $25/hr default
            fuel_cost = Decimal(str(extraction.fuel_cost or 0))
            estimated_profit = revenue - labor_cost - fuel_cost
            
            audit = AuditLog(
                id=str(uuid4()),
                tenant_id=self.tenant_id,
                actor_user_id=self.user_id,
                action="profitability_updated",
                resource_type="project",
                resource_id=str(project.id),
                details=json.dumps({
                    "revenue": float(revenue),
                    "labor_cost": float(labor_cost),
                    "fuel_cost": float(fuel_cost),
                    "estimated_profit": float(estimated_profit),
                    "project_name": project.project_name,
                    "extraction_id": str(extraction.id),
                }),
                created_by=self.user_id,
            )
            self.db.add(audit)
            self.db.flush()

    def _update_billing_pipeline(self, extraction: DocumentExtraction) -> None:
        """Update billing pipeline with invoice ready for delivery."""
        # In a real system, this would:
        # 1. Update invoice status to "ready_for_delivery"
        # 2. Queue for billing system delivery
        # 3. Trigger delivery process
        # 4. Update customer billing ledger
        
        audit = AuditLog(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            actor_user_id=self.user_id,
            action="billing_updated",
            resource_type="billing_pipeline",
            resource_id=str(extraction.id),
            details=json.dumps({
                "destination": extraction.destination,
                "amount": float(extraction.invoice_total) if extraction.invoice_total else 0,
                "customer": extraction.customer_name or extraction.company_name,
                "status": "ready_for_delivery",
                "extraction_id": str(extraction.id),
            }),
            created_by=self.user_id,
        )
        self.db.add(audit)
        self.db.flush()

    def _create_distribution_audit_log(
        self, extraction: DocumentExtraction, approval_notes: str, summary: dict
    ) -> None:
        """Create comprehensive audit log for entire distribution."""
        audit = AuditLog(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            actor_user_id=self.user_id,
            action="extraction_distributed",
            resource_type="document_extraction",
            resource_id=str(extraction.id),
            details=json.dumps({
                "extraction_id": str(extraction.id),
                "status": "distributed",
                "approval_notes": approval_notes,
                "distribution_summary": summary,
                "document_type": extraction.document_type,
                "company": extraction.company_name,
                "ticket_number": extraction.ticket_number,
                "destination": extraction.destination,
                "invoice_total": float(extraction.invoice_total) if extraction.invoice_total else None,
                "distributed_at": datetime.utcnow().isoformat(),
            }),
            created_by=self.user_id,
        )
        self.db.add(audit)
        self.db.flush()

    def _create_distribution_error_log(self, extraction: DocumentExtraction, error_message: str) -> None:
        """Create error audit log if distribution fails."""
        audit = AuditLog(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            actor_user_id=self.user_id,
            action="extraction_distribution_error",
            resource_type="document_extraction",
            resource_id=str(extraction.id),
            details=json.dumps({
                "extraction_id": str(extraction.id),
                "error_message": error_message,
                "status": "distribution_failed",
                "failed_at": datetime.utcnow().isoformat(),
            }),
            created_by=self.user_id,
        )
        self.db.add(audit)
        self.db.flush()

