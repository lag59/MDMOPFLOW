"""Service for managing human review of document extractions."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DocumentExtraction, ExtractionIssue


class ExtractionReviewService:
    """Manages human review workflow for document extractions."""

    def __init__(self, db: Session, user_id: str, tenant_id: str):
        self.db = db
        self.user_id = user_id
        self.tenant_id = tenant_id

    def get_extraction_for_review(self, extraction_id: UUID) -> Optional[DocumentExtraction]:
        return self.db.scalars(
            select(DocumentExtraction).where(
                DocumentExtraction.id == str(extraction_id),
                DocumentExtraction.tenant_id == self.tenant_id,
            )
        ).first()

    def get_extraction_issues(self, extraction_id: UUID) -> list[ExtractionIssue]:
        return list(
            self.db.scalars(
                select(ExtractionIssue)
                .where(
                    ExtractionIssue.extraction_id == str(extraction_id),
                    ExtractionIssue.tenant_id == self.tenant_id,
                )
                .order_by(ExtractionIssue.created_at.desc())
            ).all()
        )

    def submit_review(self, extraction_id: UUID, review_notes: str, corrections: dict[str, str]) -> DocumentExtraction:
        extraction = self.get_extraction_for_review(extraction_id)
        if not extraction:
            raise ValueError(f"Extraction {extraction_id} not found")
        for field_name, corrected_value in corrections.items():
            if hasattr(extraction, field_name):
                if field_name in ("tons", "invoice_total", "weight_net_lbs", "cubic_yards"):
                    try:
                        setattr(extraction, field_name, Decimal(corrected_value))
                    except Exception:
                        pass
                else:
                    setattr(extraction, field_name, corrected_value)
        extraction.reviewed_by = str(self.user_id)
        extraction.reviewed_at = datetime.utcnow()
        extraction.review_notes = review_notes
        extraction.status = "review_submitted"
        self.db.flush()
        return extraction

    def resolve_extraction_issue(self, issue_id: UUID, resolved_value: str) -> ExtractionIssue:
        issue = self.db.scalars(
            select(ExtractionIssue).where(
                ExtractionIssue.id == str(issue_id),
                ExtractionIssue.tenant_id == self.tenant_id,
            )
        ).first()
        if not issue:
            raise ValueError(f"Issue {issue_id} not found")
        issue.resolved = True
        issue.resolved_value = resolved_value
        issue.resolved_by = str(self.user_id)
        issue.resolved_at = datetime.utcnow()
        self.db.flush()
        return issue

    def calculate_extraction_confidence_score(self, extraction: DocumentExtraction) -> float:
        confidence_fields = [
            extraction.document_type_confidence,
            extraction.company_name_confidence,
            extraction.ticket_number_confidence,
            extraction.destination_confidence,
            extraction.material_confidence,
            extraction.invoice_total_confidence,
        ]
        valid_scores = [float(s) for s in confidence_fields if s and float(s) > 0]
        if not valid_scores:
            return 0.0
        return sum(valid_scores) / len(valid_scores)

    def get_pending_review_extractions(self, limit: int = 50, offset: int = 0) -> tuple[list[DocumentExtraction], int]:
        base = select(DocumentExtraction).where(
            DocumentExtraction.tenant_id == self.tenant_id,
            DocumentExtraction.status == "review_pending",
        )
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        extractions = list(
            self.db.scalars(
                base.order_by(DocumentExtraction.created_at.desc()).limit(limit).offset(offset)
            ).all()
        )
        return extractions, total

    def get_submitted_review_extractions(self, limit: int = 50, offset: int = 0) -> tuple[list[DocumentExtraction], int]:
        base = select(DocumentExtraction).where(
            DocumentExtraction.tenant_id == self.tenant_id,
            DocumentExtraction.status == "review_submitted",
        )
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        extractions = list(
            self.db.scalars(
                base.order_by(DocumentExtraction.created_at.desc()).limit(limit).offset(offset)
            ).all()
        )
        return extractions, total

    def get_extractions_by_status(
        self,
        status: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DocumentExtraction], int]:
        base = select(DocumentExtraction).where(
            DocumentExtraction.tenant_id == self.tenant_id,
            DocumentExtraction.status == status,
        )
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        extractions = list(
            self.db.scalars(
                base.order_by(DocumentExtraction.created_at.desc()).limit(limit).offset(offset)
            ).all()
        )
        return extractions, total
