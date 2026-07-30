"""Add estimate domain tables.

Revision ID: 20260729_0012
Revises: 20260728_0011
Create Date: 2026-07-29 21:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260729_0012"
down_revision = "20260728_0011"
branch_labels = None
depends_on = None


UUID_TYPE = postgresql.UUID(as_uuid=False)


def upgrade() -> None:
    op.create_table(
        "estimates",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("estimate_name", sa.String(length=255), nullable=False),
        sa.Column("estimate_number", sa.String(length=120), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("project_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("project_address", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("project_type", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("bid_due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_completion_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimator_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("project_manager_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("sales_contact", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("contract_type", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("estimate_type", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("tax_jurisdiction", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("target_margin_percent", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("default_overhead_percent", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("default_contingency_percent", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="New"),
        sa.Column("approval_status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "estimate_number", name="uq_estimates_tenant_number"),
    )
    op.create_index("ix_estimates_tenant_id", "estimates", ["tenant_id"], unique=False)
    op.create_index("ix_estimates_project_id", "estimates", ["project_id"], unique=False)
    op.create_index("ix_estimates_estimate_number", "estimates", ["estimate_number"], unique=False)
    op.create_index("ix_estimates_status", "estimates", ["status"], unique=False)

    op.create_table(
        "estimate_items",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("estimate_id", UUID_TYPE, sa.ForeignKey("estimates.id"), nullable=False),
        sa.Column("item_number", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("cost_code", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("division", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("phase", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("work_location", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("unit_of_measure", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("unit_cost", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("total_selling_price", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=60), nullable=False, server_default="manual"),
        sa.Column("assumption", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("review_status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_estimate_items_tenant_id", "estimate_items", ["tenant_id"], unique=False)
    op.create_index("ix_estimate_items_estimate_id", "estimate_items", ["estimate_id"], unique=False)

    op.create_table(
        "estimate_documents",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("estimate_id", UUID_TYPE, sa.ForeignKey("estimates.id"), nullable=False),
        sa.Column("intake_item_id", UUID_TYPE, sa.ForeignKey("intake_items.id"), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=80), nullable=False, server_default="Unknown document"),
        sa.Column("processing_status", sa.String(length=40), nullable=False, server_default="Uploaded"),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("version_label", sa.String(length=40), nullable=False, server_default="v1"),
        sa.Column("review_status", sa.String(length=40), nullable=False, server_default="Review recommended"),
        sa.Column("uploaded_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_estimate_documents_tenant_id", "estimate_documents", ["tenant_id"], unique=False)
    op.create_index("ix_estimate_documents_estimate_id", "estimate_documents", ["estimate_id"], unique=False)
    op.create_index("ix_estimate_documents_intake_item_id", "estimate_documents", ["intake_item_id"], unique=False)

    op.create_table(
        "estimate_approvals",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("estimate_id", UUID_TYPE, sa.ForeignKey("estimates.id"), nullable=False),
        sa.Column("approver_user_id", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approver_role", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("decision", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("comments", sa.Text(), nullable=False, server_default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_estimate_approvals_tenant_id", "estimate_approvals", ["tenant_id"], unique=False)
    op.create_index("ix_estimate_approvals_estimate_id", "estimate_approvals", ["estimate_id"], unique=False)

    op.create_table(
        "estimate_audit_logs",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("estimate_id", UUID_TYPE, sa.ForeignKey("estimates.id"), nullable=False),
        sa.Column("actor_user_id", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("previous_status", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("new_status", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("details", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_estimate_audit_logs_tenant_id", "estimate_audit_logs", ["tenant_id"], unique=False)
    op.create_index("ix_estimate_audit_logs_estimate_id", "estimate_audit_logs", ["estimate_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_estimate_audit_logs_estimate_id", table_name="estimate_audit_logs")
    op.drop_index("ix_estimate_audit_logs_tenant_id", table_name="estimate_audit_logs")
    op.drop_table("estimate_audit_logs")

    op.drop_index("ix_estimate_approvals_estimate_id", table_name="estimate_approvals")
    op.drop_index("ix_estimate_approvals_tenant_id", table_name="estimate_approvals")
    op.drop_table("estimate_approvals")

    op.drop_index("ix_estimate_documents_intake_item_id", table_name="estimate_documents")
    op.drop_index("ix_estimate_documents_estimate_id", table_name="estimate_documents")
    op.drop_index("ix_estimate_documents_tenant_id", table_name="estimate_documents")
    op.drop_table("estimate_documents")

    op.drop_index("ix_estimate_items_estimate_id", table_name="estimate_items")
    op.drop_index("ix_estimate_items_tenant_id", table_name="estimate_items")
    op.drop_table("estimate_items")

    op.drop_index("ix_estimates_status", table_name="estimates")
    op.drop_index("ix_estimates_estimate_number", table_name="estimates")
    op.drop_index("ix_estimates_project_id", table_name="estimates")
    op.drop_index("ix_estimates_tenant_id", table_name="estimates")
    op.drop_table("estimates")
