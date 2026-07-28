"""Add production query indices.

Revision ID: 20260728_0008
Revises: 20260728_0007
Create Date: 2026-07-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0008"
down_revision = "20260728_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def maybe_create_index(name: str, table_name: str, columns: list[str]) -> None:
        if not inspector.has_table(table_name):
            return
        existing = {index["name"] for index in inspector.get_indexes(table_name)}
        if name not in existing:
            op.create_index(name, table_name, columns, unique=False)

    maybe_create_index(
        "ix_intake_items_tenant_id_needs_review_created_at",
        "intake_items",
        ["tenant_id", "needs_review", "created_at"],
    )
    maybe_create_index(
        "ix_document_extractions_tenant_id_status_created_at",
        "document_extractions",
        ["tenant_id", "status", "created_at"],
    )
    maybe_create_index(
        "ix_tickets_tenant_id_status_created_at",
        "tickets",
        ["tenant_id", "status", "created_at"],
    )
    maybe_create_index(
        "ix_audit_logs_tenant_id_created_at",
        "audit_logs",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant_id_created_at", table_name="audit_logs")
    op.drop_index("ix_tickets_tenant_id_status_created_at", table_name="tickets")
    op.drop_index("ix_document_extractions_tenant_id_status_created_at", table_name="document_extractions")
    op.drop_index("ix_intake_items_tenant_id_needs_review_created_at", table_name="intake_items")
