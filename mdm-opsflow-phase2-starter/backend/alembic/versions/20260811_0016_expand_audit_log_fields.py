"""Expand audit logs with immutable metadata and snapshots.

Revision ID: 20260811_0016
Revises: 20260811_0015
Create Date: 2026-08-11 23:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260811_0016"
down_revision = "20260811_0015"
branch_labels = None
depends_on = None


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("audit_logs"):
        return

    columns = {column["name"] for column in inspector.get_columns("audit_logs")}

    tenant_column = next((column for column in inspector.get_columns("audit_logs") if column["name"] == "tenant_id"), None)
    if tenant_column is not None and tenant_column.get("nullable") is False:
        op.alter_column("audit_logs", "tenant_id", nullable=True)

    if "request_id" not in columns:
        op.add_column("audit_logs", sa.Column("request_id", sa.String(length=80), nullable=True))
    if "before_values_json" not in columns:
        op.add_column(
            "audit_logs",
            sa.Column("before_values_json", sa.Text(), nullable=False, server_default=""),
        )
    if "after_values_json" not in columns:
        op.add_column(
            "audit_logs",
            sa.Column("after_values_json", sa.Text(), nullable=False, server_default=""),
        )
    if "occurred_at" not in columns:
        op.add_column(
            "audit_logs",
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        )

    op.execute(sa.text("UPDATE audit_logs SET occurred_at = created_at WHERE occurred_at IS NULL"))
    op.alter_column("audit_logs", "occurred_at", nullable=False)

    indexes = _index_names(inspector, "audit_logs")
    if "ix_audit_logs_request_id" not in indexes:
        op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("audit_logs"):
        return

    tenant_column = next((column for column in inspector.get_columns("audit_logs") if column["name"] == "tenant_id"), None)
    if tenant_column is not None and tenant_column.get("nullable") is True:
        op.execute(sa.text("DELETE FROM audit_logs WHERE tenant_id IS NULL"))
        op.alter_column("audit_logs", "tenant_id", nullable=False)

    indexes = _index_names(inspector, "audit_logs")
    if "ix_audit_logs_request_id" in indexes:
        op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")

    columns = {column["name"] for column in inspector.get_columns("audit_logs")}
    for column_name in ["occurred_at", "after_values_json", "before_values_json", "request_id"]:
        if column_name in columns:
            op.drop_column("audit_logs", column_name)
