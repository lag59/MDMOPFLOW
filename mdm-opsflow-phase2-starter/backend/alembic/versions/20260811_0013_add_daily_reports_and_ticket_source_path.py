"""Add daily field reports table and ticket source document path column.

Revision ID: 20260811_0013
Revises: 20260729_0012
Create Date: 2026-08-11 19:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260811_0013"
down_revision = "20260729_0012"
branch_labels = None
depends_on = None


UUID_TYPE = postgresql.UUID(as_uuid=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("daily_field_reports"):
        op.create_table(
            "daily_field_reports",
            sa.Column("id", UUID_TYPE, nullable=False),
            sa.Column("tenant_id", UUID_TYPE, nullable=False),
            sa.Column("project_id", UUID_TYPE, nullable=False),
            sa.Column("report_number", sa.String(length=80), nullable=False),
            sa.Column("report_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("company_name", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("reporting_supervisor", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("shift_start_time", sa.String(length=20), nullable=False, server_default=""),
            sa.Column("shift_end_time", sa.String(length=20), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
            sa.Column("weather", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("work_performed", sa.Text(), nullable=False, server_default=""),
            sa.Column("work_planned_for_tomorrow", sa.Text(), nullable=False, server_default=""),
            sa.Column("crew_members", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("equipment_used", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("deliveries", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("visitors", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("delays", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("photos", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("production_quantities", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("safety_observations", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("prepared_by", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("electronic_signature", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("submitted_by", UUID_TYPE, nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reviewed_by", UUID_TYPE, nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by", UUID_TYPE, nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", UUID_TYPE, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    daily_indexes = {idx["name"] for idx in inspector.get_indexes("daily_field_reports")} if inspector.has_table("daily_field_reports") else set()
    if "ix_daily_field_reports_tenant_id" not in daily_indexes:
        op.create_index("ix_daily_field_reports_tenant_id", "daily_field_reports", ["tenant_id"], unique=False)
    if "ix_daily_field_reports_project_id" not in daily_indexes:
        op.create_index("ix_daily_field_reports_project_id", "daily_field_reports", ["project_id"], unique=False)
    if "ix_daily_field_reports_report_number" not in daily_indexes:
        op.create_index("ix_daily_field_reports_report_number", "daily_field_reports", ["report_number"], unique=False)

    if inspector.has_table("tickets"):
        ticket_columns = {column["name"] for column in inspector.get_columns("tickets")}
        if "source_document_path" not in ticket_columns:
            op.add_column(
                "tickets",
                sa.Column("source_document_path", sa.String(length=1024), nullable=False, server_default=""),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("tickets"):
        ticket_columns = {column["name"] for column in inspector.get_columns("tickets")}
        if "source_document_path" in ticket_columns:
            op.drop_column("tickets", "source_document_path")

    if inspector.has_table("daily_field_reports"):
        daily_indexes = {idx["name"] for idx in inspector.get_indexes("daily_field_reports")}
        if "ix_daily_field_reports_report_number" in daily_indexes:
            op.drop_index("ix_daily_field_reports_report_number", table_name="daily_field_reports")
        if "ix_daily_field_reports_project_id" in daily_indexes:
            op.drop_index("ix_daily_field_reports_project_id", table_name="daily_field_reports")
        if "ix_daily_field_reports_tenant_id" in daily_indexes:
            op.drop_index("ix_daily_field_reports_tenant_id", table_name="daily_field_reports")
        op.drop_table("daily_field_reports")