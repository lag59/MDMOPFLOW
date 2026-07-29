"""Add payroll tables.

Revision ID: 20260728_0009
Revises: 20260728_0008
Create Date: 2026-07-28 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260728_0009"
down_revision = "20260728_0008"
branch_labels = None
depends_on = None


UUID_TYPE = postgresql.UUID(as_uuid=False)


def upgrade() -> None:
    op.create_table(
        "payroll_timecards",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", UUID_TYPE, sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("project_id", UUID_TYPE, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("work_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("regular_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("overtime_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("double_time_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("cost_code", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("work_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payroll_timecards_tenant_id", "payroll_timecards", ["tenant_id"], unique=False)
    op.create_index("ix_payroll_timecards_employee_id", "payroll_timecards", ["employee_id"], unique=False)
    op.create_index("ix_payroll_timecards_project_id", "payroll_timecards", ["project_id"], unique=False)

    op.create_table(
        "payroll_runs",
        sa.Column("id", UUID_TYPE, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID_TYPE, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("run_number", sa.String(length=120), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("employee_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_regular_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_overtime_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_double_time_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", UUID_TYPE, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payroll_runs_tenant_id", "payroll_runs", ["tenant_id"], unique=False)
    op.create_index("ix_payroll_runs_run_number", "payroll_runs", ["run_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payroll_runs_run_number", table_name="payroll_runs")
    op.drop_index("ix_payroll_runs_tenant_id", table_name="payroll_runs")
    op.drop_table("payroll_runs")

    op.drop_index("ix_payroll_timecards_project_id", table_name="payroll_timecards")
    op.drop_index("ix_payroll_timecards_employee_id", table_name="payroll_timecards")
    op.drop_index("ix_payroll_timecards_tenant_id", table_name="payroll_timecards")
    op.drop_table("payroll_timecards")
