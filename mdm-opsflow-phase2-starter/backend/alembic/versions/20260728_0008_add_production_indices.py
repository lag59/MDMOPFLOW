"""Add production query indices.

Revision ID: 20260728_0008
Revises: 20260728_0007
Create Date: 2026-07-28 00:00:00.000000
"""

from alembic import op


revision = "20260728_0008"
down_revision = "20260728_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_intake_items_tenant_id_needs_review_created_at",
        "intake_items",
        ["tenant_id", "needs_review", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_document_extractions_tenant_id_status_created_at",
        "document_extractions",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_tickets_tenant_id_status_created_at",
        "tickets",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_tenant_id_created_at",
        "audit_logs",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant_id_created_at", table_name="audit_logs")
    op.drop_index("ix_tickets_tenant_id_status_created_at", table_name="tickets")
    op.drop_index("ix_document_extractions_tenant_id_status_created_at", table_name="document_extractions")
    op.drop_index("ix_intake_items_tenant_id_needs_review_created_at", table_name="intake_items")
