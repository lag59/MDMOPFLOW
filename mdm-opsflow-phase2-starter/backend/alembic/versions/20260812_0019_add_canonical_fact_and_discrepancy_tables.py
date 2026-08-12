"""Add normalized canonical extraction fact and discrepancy tables.

Revision ID: 20260812_0019
Revises: 20260812_0018
Create Date: 2026-08-12 01:25:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260812_0019"
down_revision = "20260812_0018"
branch_labels = None
depends_on = None


UUID_TYPE = postgresql.UUID(as_uuid=False)


def upgrade() -> None:
    op.create_table(
        "extraction_canonical_facts",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("extraction_id", UUID_TYPE, sa.ForeignKey("document_extractions.id"), nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("field_key", sa.String(length=120), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("value_num", sa.Numeric(14, 4), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("source_document_type", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("source_item_id", UUID_TYPE, sa.ForeignKey("intake_items.id"), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("authority_level", sa.String(length=40), nullable=False, server_default="informational"),
        sa.Column("effective_date", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_extraction_canonical_facts_extraction_id", "extraction_canonical_facts", ["extraction_id"], unique=False)
    op.create_index("ix_extraction_canonical_facts_tenant_id", "extraction_canonical_facts", ["tenant_id"], unique=False)

    op.create_table(
        "extraction_discrepancies",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("extraction_id", UUID_TYPE, sa.ForeignKey("document_extractions.id"), nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("discrepancy_key", sa.String(length=120), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="warning"),
        sa.Column("candidate_values_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("recommended_value_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resolved_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_extraction_discrepancies_extraction_id", "extraction_discrepancies", ["extraction_id"], unique=False)
    op.create_index("ix_extraction_discrepancies_tenant_id", "extraction_discrepancies", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_extraction_discrepancies_tenant_id", table_name="extraction_discrepancies")
    op.drop_index("ix_extraction_discrepancies_extraction_id", table_name="extraction_discrepancies")
    op.drop_table("extraction_discrepancies")

    op.drop_index("ix_extraction_canonical_facts_tenant_id", table_name="extraction_canonical_facts")
    op.drop_index("ix_extraction_canonical_facts_extraction_id", table_name="extraction_canonical_facts")
    op.drop_table("extraction_canonical_facts")
