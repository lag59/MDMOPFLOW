"""Add tenant material density presets

Revision ID: 20260725_0003
Revises: 20260720_0002
Create Date: 2026-07-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260725_0003"
down_revision = "20260720_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "material_density_presets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("material_name", sa.String(length=120), nullable=False),
        sa.Column("density_tons_per_cubic_yard", sa.Numeric(10, 4), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "material_name", name="uq_material_density_presets_tenant_material"),
    )
    op.create_index("ix_material_density_presets_tenant_id", "material_density_presets", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_material_density_presets_tenant_id", table_name="material_density_presets")
    op.drop_table("material_density_presets")
