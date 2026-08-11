"""Seed formal permission matrix for tenant roles.

Revision ID: 20260811_0015
Revises: 20260811_0014
Create Date: 2026-08-11 22:55:00.000000
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260811_0015"
down_revision = "20260811_0014"
branch_labels = None
depends_on = None


ROLE_PERMISSION_MATRIX: dict[str, list[str]] = {
    "tenant_admin": [
        "project.view",
        "project.manage",
        "project.approve",
        "intake.view",
        "intake.manage",
        "intake.review",
        "estimate.view",
        "estimate.create",
        "estimate.edit",
        "dispatch.view",
        "dispatch.manage",
        "finance.view",
        "finance.manage",
        "finance.approve",
        "payroll.view",
        "payroll.process",
        "safety.view",
        "safety.manage",
        "fleet.view",
        "fleet.manage",
        "user.view",
        "user.manage",
        "membership.assign",
        "billing.view",
        "billing.manage",
        "ai.assignment.view",
        "ai.assignment.manage",
        "extraction.view",
        "extraction.review",
        "extraction.approve",
    ],
    "owner": [
        "project.view",
        "project.manage",
        "project.approve",
        "intake.view",
        "intake.manage",
        "intake.review",
        "estimate.view",
        "finance.view",
        "finance.approve",
        "payroll.view",
        "safety.view",
        "fleet.view",
        "user.view",
        "user.manage",
        "membership.assign",
        "billing.view",
        "billing.manage",
        "portal.vendor.submit",
        "ai.assignment.view",
        "ai.assignment.manage",
        "extraction.view",
        "extraction.review",
        "extraction.approve",
    ],
    "executive": [
        "project.view",
        "intake.view",
        "estimate.view",
        "finance.view",
        "payroll.view",
        "safety.view",
        "fleet.view",
        "user.view",
        "user.manage",
        "membership.assign",
        "billing.view",
        "ai.assignment.view",
        "extraction.view",
    ],
    "project_manager": [
        "project.view",
        "project.manage",
        "intake.view",
        "intake.manage",
        "intake.review",
        "estimate.view",
        "estimate.create",
        "estimate.edit",
        "dispatch.view",
        "dispatch.manage",
        "safety.view",
        "safety.manage",
        "user.view",
        "user.manage",
        "membership.assign",
        "portal.vendor.submit",
        "ai.assignment.view",
        "ai.assignment.manage",
        "extraction.view",
        "extraction.review",
    ],
    "estimator": [
        "estimate.view",
        "estimate.create",
        "estimate.edit",
        "project.view",
        "intake.view",
        "intake.review",
        "user.view",
        "user.manage",
        "membership.assign",
        "extraction.view",
    ],
    "field_supervisor": [
        "project.view",
        "project.manage",
        "intake.view",
        "intake.manage",
        "safety.view",
        "safety.manage",
        "dispatch.view",
        "extraction.view",
        "user.view",
    ],
    "dispatcher": [
        "dispatch.view",
        "dispatch.manage",
        "project.view",
        "fleet.view",
        "intake.view",
        "extraction.view",
    ],
    "accounting": [
        "finance.view",
        "finance.manage",
        "billing.view",
        "billing.manage",
        "project.view",
        "estimate.view",
        "intake.view",
        "extraction.view",
    ],
    "payroll": [
        "payroll.view",
        "payroll.process",
        "project.view",
        "intake.view",
        "extraction.view",
    ],
    "safety_manager": [
        "safety.view",
        "safety.manage",
        "project.view",
        "intake.view",
    ],
    "fleet_manager": [
        "fleet.view",
        "fleet.manage",
        "dispatch.view",
        "dispatch.manage",
        "project.view",
        "intake.view",
    ],
    "administrator": [
        "user.view",
        "user.manage",
        "membership.assign",
        "billing.view",
        "billing.manage",
        "ai.assignment.view",
        "ai.assignment.manage",
        "project.view",
        "project.manage",
        "intake.view",
        "intake.manage",
        "extraction.view",
        "extraction.review",
        "extraction.approve",
    ],
    "customer": ["portal.customer.view", "project.view", "intake.view"],
    "vendor": ["portal.vendor.submit", "project.view", "intake.view"],
}


def _permissions_csv(role_name: str) -> str:
    return ",".join(ROLE_PERMISSION_MATRIX[role_name])


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("roles") or not inspector.has_table("tenants"):
        return

    role_rows = bind.execute(
        sa.text("SELECT id, tenant_id, name FROM roles")
    ).mappings().all()

    role_lookup: dict[tuple[str, str], str] = {}
    for row in role_rows:
        role_lookup[(row["tenant_id"], row["name"])] = row["id"]

    tenant_ids = [row["id"] for row in bind.execute(sa.text("SELECT id FROM tenants")).mappings().all()]
    now = datetime.now(timezone.utc)

    for tenant_id in tenant_ids:
        for role_name, permissions in ROLE_PERMISSION_MATRIX.items():
            existing_role_id = role_lookup.get((tenant_id, role_name))
            permissions_csv = ",".join(permissions)
            if existing_role_id:
                bind.execute(
                    sa.text("UPDATE roles SET permissions = :permissions, updated_at = :updated_at WHERE id = :role_id"),
                    {
                        "permissions": permissions_csv,
                        "updated_at": now,
                        "role_id": existing_role_id,
                    },
                )
                continue

            new_role_id = str(uuid4())
            bind.execute(
                sa.text(
                    """
                    INSERT INTO roles (id, tenant_id, name, permissions, created_by, created_at, updated_at)
                    VALUES (:id, :tenant_id, :name, :permissions, :created_by, :created_at, :updated_at)
                    """
                ),
                {
                    "id": new_role_id,
                    "tenant_id": tenant_id,
                    "name": role_name,
                    "permissions": permissions_csv,
                    "created_by": "00000000-0000-0000-0000-000000000000",
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    # Data migration only. We intentionally keep seeded role permission updates.
    return
