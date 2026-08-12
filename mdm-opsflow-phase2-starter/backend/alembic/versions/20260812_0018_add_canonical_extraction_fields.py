"""Add canonical extraction persistence fields.

Revision ID: 20260812_0018
Revises: 20260811_0017
Create Date: 2026-08-12 00:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260812_0018"
down_revision = "20260811_0017"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(column.get("name") == column_name for column in columns)


def upgrade() -> None:
    with op.batch_alter_table("document_extractions") as batch_op:
        if not _has_column("document_extractions", "canonical_profile"):
            batch_op.add_column(sa.Column("canonical_profile", sa.String(length=50), nullable=False, server_default=""))
        if not _has_column("document_extractions", "canonical_revision"):
            batch_op.add_column(sa.Column("canonical_revision", sa.Integer(), nullable=False, server_default="1"))
        if not _has_column("document_extractions", "canonical_payload_json"):
            batch_op.add_column(sa.Column("canonical_payload_json", sa.Text(), nullable=False, server_default=""))
        if not _has_column("document_extractions", "canonical_discrepancies_json"):
            batch_op.add_column(sa.Column("canonical_discrepancies_json", sa.Text(), nullable=False, server_default=""))

    op.execute("UPDATE document_extractions SET canonical_revision = 1 WHERE canonical_revision IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("document_extractions") as batch_op:
        if _has_column("document_extractions", "canonical_discrepancies_json"):
            batch_op.drop_column("canonical_discrepancies_json")
        if _has_column("document_extractions", "canonical_payload_json"):
            batch_op.drop_column("canonical_payload_json")
        if _has_column("document_extractions", "canonical_revision"):
            batch_op.drop_column("canonical_revision")
        if _has_column("document_extractions", "canonical_profile"):
            batch_op.drop_column("canonical_profile")
