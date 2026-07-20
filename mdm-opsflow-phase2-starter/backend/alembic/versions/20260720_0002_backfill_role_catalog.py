"""Backfill role names and permissions to role catalog

Revision ID: 20260720_0002
Revises: 20260719_0001
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260720_0002"
down_revision = "20260719_0001"
branch_labels = None
depends_on = None


ROLE_PERMISSIONS = {
    "tenant_admin": "project_read,project_write,project_approve,estimate_read,estimate_write,dispatch_read,dispatch_write,finance_read,finance_write,finance_approve,payroll_read,payroll_write,safety_read,safety_write,fleet_read,fleet_write,admin_read,admin_write",
    "owner": "project_read,project_write,project_approve,estimate_read,finance_read,finance_approve,payroll_read,safety_read,fleet_read,admin_read",
    "executive": "project_read,estimate_read,finance_read,payroll_read,safety_read,fleet_read",
    "project_manager": "project_read,project_write,estimate_read,dispatch_read,dispatch_write,safety_read,safety_write",
    "estimator": "estimate_read,estimate_write,project_read",
    "dispatcher": "dispatch_read,dispatch_write,project_read,fleet_read",
    "accounting": "finance_read,finance_write,project_read,estimate_read",
    "payroll": "payroll_read,payroll_write,project_read",
    "safety_manager": "safety_read,safety_write,project_read",
    "fleet_manager": "fleet_read,fleet_write,dispatch_read,dispatch_write,project_read",
    "administrator": "admin_read,admin_write,project_read,project_write",
    "customer": "portal_customer_read,project_read",
    "vendor": "portal_vendor_write,project_read",
}

LEGACY_NAME_MAP = {
    "tenant_owner": "owner",
}


def upgrade() -> None:
    conn = op.get_bind()

    for old_name, new_name in LEGACY_NAME_MAP.items():
        conn.execute(
            sa.text("UPDATE roles SET name = :new_name WHERE name = :old_name"),
            {"new_name": new_name, "old_name": old_name},
        )

    for role_name, permissions in ROLE_PERMISSIONS.items():
        conn.execute(
            sa.text("UPDATE roles SET permissions = :permissions WHERE name = :role_name"),
            {"permissions": permissions, "role_name": role_name},
        )


def downgrade() -> None:
    conn = op.get_bind()

    for old_name, new_name in LEGACY_NAME_MAP.items():
        conn.execute(
            sa.text("UPDATE roles SET name = :old_name WHERE name = :new_name"),
            {"old_name": old_name, "new_name": new_name},
        )
