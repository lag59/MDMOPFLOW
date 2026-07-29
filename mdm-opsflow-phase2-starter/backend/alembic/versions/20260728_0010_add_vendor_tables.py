"""Add vendor portal tables.

Revision ID: 20260728_0010
Revises: 20260728_0009
Create Date: 2026-07-28 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260728_0010"
down_revision = "20260728_0009"
branch_labels = None
depends_on = None


UUID_TYPE = postgresql.UUID(as_uuid=False)


def upgrade() -> None:
    op.create_table(
        "vendor_purchase_orders",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("po_number", sa.String(length=120), nullable=False),
        sa.Column("vendor_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vendor_purchase_orders_tenant_id", "vendor_purchase_orders", ["tenant_id"], unique=False)
    op.create_index("ix_vendor_purchase_orders_project_id", "vendor_purchase_orders", ["project_id"], unique=False)
    op.create_index("ix_vendor_purchase_orders_po_number", "vendor_purchase_orders", ["po_number"], unique=False)

    op.create_table(
        "vendor_invoice_submissions",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("purchase_order_id", UUID_TYPE, sa.ForeignKey("vendor_purchase_orders.id"), nullable=True),
        sa.Column("invoice_number", sa.String(length=120), nullable=False),
        sa.Column("vendor_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="submitted"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vendor_invoice_submissions_tenant_id", "vendor_invoice_submissions", ["tenant_id"], unique=False)
    op.create_index("ix_vendor_invoice_submissions_project_id", "vendor_invoice_submissions", ["project_id"], unique=False)
    op.create_index("ix_vendor_invoice_submissions_purchase_order_id", "vendor_invoice_submissions", ["purchase_order_id"], unique=False)
    op.create_index("ix_vendor_invoice_submissions_invoice_number", "vendor_invoice_submissions", ["invoice_number"], unique=False)

    op.create_table(
        "vendor_delivery_records",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("purchase_order_id", UUID_TYPE, sa.ForeignKey("vendor_purchase_orders.id"), nullable=True),
        sa.Column("ticket_number", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("vendor_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("destination", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vendor_delivery_records_tenant_id", "vendor_delivery_records", ["tenant_id"], unique=False)
    op.create_index("ix_vendor_delivery_records_project_id", "vendor_delivery_records", ["project_id"], unique=False)
    op.create_index("ix_vendor_delivery_records_purchase_order_id", "vendor_delivery_records", ["purchase_order_id"], unique=False)
    op.create_index("ix_vendor_delivery_records_ticket_number", "vendor_delivery_records", ["ticket_number"], unique=False)

    op.create_table(
        "vendor_compliance_documents",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("document_name", sa.String(length=255), nullable=False),
        sa.Column("vendor_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="current"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vendor_compliance_documents_tenant_id", "vendor_compliance_documents", ["tenant_id"], unique=False)
    op.create_index("ix_vendor_compliance_documents_project_id", "vendor_compliance_documents", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_vendor_compliance_documents_project_id", table_name="vendor_compliance_documents")
    op.drop_index("ix_vendor_compliance_documents_tenant_id", table_name="vendor_compliance_documents")
    op.drop_table("vendor_compliance_documents")

    op.drop_index("ix_vendor_delivery_records_ticket_number", table_name="vendor_delivery_records")
    op.drop_index("ix_vendor_delivery_records_purchase_order_id", table_name="vendor_delivery_records")
    op.drop_index("ix_vendor_delivery_records_project_id", table_name="vendor_delivery_records")
    op.drop_index("ix_vendor_delivery_records_tenant_id", table_name="vendor_delivery_records")
    op.drop_table("vendor_delivery_records")

    op.drop_index("ix_vendor_invoice_submissions_invoice_number", table_name="vendor_invoice_submissions")
    op.drop_index("ix_vendor_invoice_submissions_purchase_order_id", table_name="vendor_invoice_submissions")
    op.drop_index("ix_vendor_invoice_submissions_project_id", table_name="vendor_invoice_submissions")
    op.drop_index("ix_vendor_invoice_submissions_tenant_id", table_name="vendor_invoice_submissions")
    op.drop_table("vendor_invoice_submissions")

    op.drop_index("ix_vendor_purchase_orders_po_number", table_name="vendor_purchase_orders")
    op.drop_index("ix_vendor_purchase_orders_project_id", table_name="vendor_purchase_orders")
    op.drop_index("ix_vendor_purchase_orders_tenant_id", table_name="vendor_purchase_orders")
    op.drop_table("vendor_purchase_orders")
