"""Add estimator workflow tables.

Revision ID: 20260728_0011
Revises: 20260728_0010
Create Date: 2026-07-28 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260728_0011"
down_revision = "20260728_0010"
branch_labels = None
depends_on = None


UUID_TYPE = postgresql.UUID(as_uuid=False)


def upgrade() -> None:
    op.create_table(
        "estimator_takeoffs",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("takeoff_number", sa.String(length=120), nullable=False),
        sa.Column("material_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("unit_of_measure", sa.String(length=40), nullable=False, server_default="cy"),
        sa.Column("estimated_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_estimator_takeoffs_tenant_id", "estimator_takeoffs", ["tenant_id"], unique=False)
    op.create_index("ix_estimator_takeoffs_project_id", "estimator_takeoffs", ["project_id"], unique=False)
    op.create_index("ix_estimator_takeoffs_takeoff_number", "estimator_takeoffs", ["takeoff_number"], unique=False)

    op.create_table(
        "estimator_versions",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("version_name", sa.String(length=120), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("estimated_revenue", sa.Numeric(12, 2), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_estimator_versions_tenant_id", "estimator_versions", ["tenant_id"], unique=False)
    op.create_index("ix_estimator_versions_project_id", "estimator_versions", ["project_id"], unique=False)
    op.create_index("ix_estimator_versions_version_name", "estimator_versions", ["version_name"], unique=False)

    op.create_table(
        "estimator_bid_pipeline_items",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("bid_number", sa.String(length=120), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("stage", sa.String(length=40), nullable=False, server_default="qualifying"),
        sa.Column("bid_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("probability_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_estimator_bid_pipeline_items_tenant_id", "estimator_bid_pipeline_items", ["tenant_id"], unique=False)
    op.create_index("ix_estimator_bid_pipeline_items_project_id", "estimator_bid_pipeline_items", ["project_id"], unique=False)
    op.create_index("ix_estimator_bid_pipeline_items_bid_number", "estimator_bid_pipeline_items", ["bid_number"], unique=False)

    op.create_table(
        "estimator_win_loss_records",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("bid_pipeline_item_id", UUID_TYPE, sa.ForeignKey("estimator_bid_pipeline_items.id"), nullable=True),
        sa.Column("outcome", sa.String(length=10), nullable=False, server_default="pending"),
        sa.Column("final_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("decision_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_estimator_win_loss_records_tenant_id", "estimator_win_loss_records", ["tenant_id"], unique=False)
    op.create_index("ix_estimator_win_loss_records_project_id", "estimator_win_loss_records", ["project_id"], unique=False)
    op.create_index("ix_estimator_win_loss_records_bid_pipeline_item_id", "estimator_win_loss_records", ["bid_pipeline_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_estimator_win_loss_records_bid_pipeline_item_id", table_name="estimator_win_loss_records")
    op.drop_index("ix_estimator_win_loss_records_project_id", table_name="estimator_win_loss_records")
    op.drop_index("ix_estimator_win_loss_records_tenant_id", table_name="estimator_win_loss_records")
    op.drop_table("estimator_win_loss_records")

    op.drop_index("ix_estimator_bid_pipeline_items_bid_number", table_name="estimator_bid_pipeline_items")
    op.drop_index("ix_estimator_bid_pipeline_items_project_id", table_name="estimator_bid_pipeline_items")
    op.drop_index("ix_estimator_bid_pipeline_items_tenant_id", table_name="estimator_bid_pipeline_items")
    op.drop_table("estimator_bid_pipeline_items")

    op.drop_index("ix_estimator_versions_version_name", table_name="estimator_versions")
    op.drop_index("ix_estimator_versions_project_id", table_name="estimator_versions")
    op.drop_index("ix_estimator_versions_tenant_id", table_name="estimator_versions")
    op.drop_table("estimator_versions")

    op.drop_index("ix_estimator_takeoffs_takeoff_number", table_name="estimator_takeoffs")
    op.drop_index("ix_estimator_takeoffs_project_id", table_name="estimator_takeoffs")
    op.drop_index("ix_estimator_takeoffs_tenant_id", table_name="estimator_takeoffs")
    op.drop_table("estimator_takeoffs")
