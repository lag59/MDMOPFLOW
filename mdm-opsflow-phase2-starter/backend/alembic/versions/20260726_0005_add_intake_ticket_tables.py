"""Add ingestion, intake, integration, and ticket tables.

Revision ID: 20260726_0005
Revises: 20260725_0003
Create Date: 2026-07-26 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260726_0005"
down_revision = "20260725_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def has_index(table_name: str, index_name: str) -> bool:
        if not inspector.has_table(table_name):
            return False
        return index_name in {index["name"] for index in inspector.get_indexes(table_name)}

    if not inspector.has_table("ingestion_batches"):
        op.create_table(
            "ingestion_batches",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("source_channel", sa.String(length=120), nullable=False, server_default="upload"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="queued"),
            sa.Column("total_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("matched_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("needs_review_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duplicate_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("blocked_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("summary_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_by", sa.UUID(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_index("ingestion_batches", "ix_ingestion_batches_tenant_id"):
        op.create_index("ix_ingestion_batches_tenant_id", "ingestion_batches", ["tenant_id"], unique=False)

    if not inspector.has_table("intake_items"):
        op.create_table(
            "intake_items",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("batch_id", sa.UUID(), nullable=True),
            sa.Column("project_id", sa.UUID(), nullable=True),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("file_path", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("mime_type", sa.String(length=120), nullable=False, server_default="application/octet-stream"),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("page_document_index", sa.Integer(), nullable=True),
            sa.Column("document_type", sa.String(length=120), nullable=False, server_default="general"),
            sa.Column("classification_confidence", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("match_confidence", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("source", sa.String(length=120), nullable=False, server_default="manual"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="uploaded"),
            sa.Column("processing_stage", sa.String(length=50), nullable=False, server_default="uploaded"),
            sa.Column("extracted_summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("ai_summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("extracted_entities", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("ocr_status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("ai_status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("review_reason", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("duplicate_of_item_id", sa.UUID(), nullable=True),
            sa.Column("conflict_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("reviewed_by", sa.UUID(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.UUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.ForeignKeyConstraint(["batch_id"], ["ingestion_batches.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["duplicate_of_item_id"], ["intake_items.id"]),
            sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_index("intake_items", "ix_intake_items_tenant_id"):
        op.create_index("ix_intake_items_tenant_id", "intake_items", ["tenant_id"], unique=False)
    if not has_index("intake_items", "ix_intake_items_batch_id"):
        op.create_index("ix_intake_items_batch_id", "intake_items", ["batch_id"], unique=False)
    if not has_index("intake_items", "ix_intake_items_content_hash"):
        op.create_index("ix_intake_items_content_hash", "intake_items", ["content_hash"], unique=False)

    if not inspector.has_table("integration_events"):
        op.create_table(
            "integration_events",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("event_type", sa.String(length=120), nullable=False),
            sa.Column("resource_type", sa.String(length=120), nullable=False),
            sa.Column("resource_id", sa.String(length=120), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("created_by", sa.UUID(), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_index("integration_events", "ix_integration_events_tenant_id"):
        op.create_index("ix_integration_events_tenant_id", "integration_events", ["tenant_id"], unique=False)
    if not has_index("integration_events", "ix_integration_events_event_type"):
        op.create_index("ix_integration_events_event_type", "integration_events", ["event_type"], unique=False)

    if not inspector.has_table("tickets"):
        op.create_table(
            "tickets",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("intake_item_id", sa.UUID(), nullable=True),
            sa.Column("project_id", sa.UUID(), nullable=True),
            sa.Column("ticket_number", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("truck", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("driver", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("material", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("origin", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("destination", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("load_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("unload_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("miles", sa.Numeric(10, 2), nullable=True),
            sa.Column("weight", sa.Numeric(12, 2), nullable=True),
            sa.Column("volume_yards", sa.Numeric(12, 2), nullable=True),
            sa.Column("tons", sa.Numeric(12, 2), nullable=True),
            sa.Column("fuel_cost", sa.Numeric(12, 2), nullable=True),
            sa.Column("revenue", sa.Numeric(12, 2), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_by", sa.UUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.ForeignKeyConstraint(["intake_item_id"], ["intake_items.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_index("tickets", "ix_tickets_tenant_id"):
        op.create_index("ix_tickets_tenant_id", "tickets", ["tenant_id"], unique=False)
    if not has_index("tickets", "ix_tickets_project_id"):
        op.create_index("ix_tickets_project_id", "tickets", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tickets_project_id", table_name="tickets")
    op.drop_index("ix_tickets_tenant_id", table_name="tickets")
    op.drop_table("tickets")

    op.drop_index("ix_integration_events_event_type", table_name="integration_events")
    op.drop_index("ix_integration_events_tenant_id", table_name="integration_events")
    op.drop_table("integration_events")

    op.drop_index("ix_intake_items_content_hash", table_name="intake_items")
    op.drop_index("ix_intake_items_batch_id", table_name="intake_items")
    op.drop_index("ix_intake_items_tenant_id", table_name="intake_items")
    op.drop_table("intake_items")

    op.drop_index("ix_ingestion_batches_tenant_id", table_name="ingestion_batches")
    op.drop_table("ingestion_batches")