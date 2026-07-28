"""Add per-user permission overrides for tenant members.

Revision ID: 20260728_0007
Revises: 20260727_0006
Create Date: 2026-07-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260728_0007"
down_revision = "20260727_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("user_permission_overrides"):
        op.create_table(
            "user_permission_overrides",
            sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("permission", sa.String(length=120), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "user_id", "permission", name="uq_user_permission_overrides_scope"),
        )

    index_names = {index["name"] for index in inspector.get_indexes("user_permission_overrides")} if inspector.has_table("user_permission_overrides") else set()
    tenant_index = op.f("ix_user_permission_overrides_tenant_id")
    user_index = op.f("ix_user_permission_overrides_user_id")
    if tenant_index not in index_names:
        op.create_index(tenant_index, "user_permission_overrides", ["tenant_id"], unique=False)
    if user_index not in index_names:
        op.create_index(user_index, "user_permission_overrides", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_permission_overrides_user_id"), table_name="user_permission_overrides")
    op.drop_index(op.f("ix_user_permission_overrides_tenant_id"), table_name="user_permission_overrides")
    op.drop_table("user_permission_overrides")
