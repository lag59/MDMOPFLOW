"""Add test data classification fields for tenants and users.

Revision ID: 20260811_0014
Revises: 20260811_0013
Create Date: 2026-08-11 21:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260811_0014"
down_revision = "20260811_0013"
branch_labels = None
depends_on = None


TENANT_TYPE_ENUM = sa.Enum("production", "demo", "test", "canary", name="tenanttype")


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    TENANT_TYPE_ENUM.create(bind, checkfirst=True)

    if inspector.has_table("tenants"):
        tenant_columns = {column["name"] for column in inspector.get_columns("tenants")}
        if "tenant_type" not in tenant_columns:
            op.add_column(
                "tenants",
                sa.Column("tenant_type", TENANT_TYPE_ENUM, nullable=False, server_default="production"),
            )
        if "is_test" not in tenant_columns:
            op.add_column("tenants", sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "created_by_automation" not in tenant_columns:
            op.add_column(
                "tenants", sa.Column("created_by_automation", sa.Boolean(), nullable=False, server_default=sa.false())
            )
        if "test_run_id" not in tenant_columns:
            op.add_column("tenants", sa.Column("test_run_id", sa.String(length=120), nullable=True))
        if "expires_at" not in tenant_columns:
            op.add_column("tenants", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    if inspector.has_table("users"):
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "is_test" not in user_columns:
            op.add_column("users", sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "created_by_automation" not in user_columns:
            op.add_column(
                "users", sa.Column("created_by_automation", sa.Boolean(), nullable=False, server_default=sa.false())
            )
        if "test_run_id" not in user_columns:
            op.add_column("users", sa.Column("test_run_id", sa.String(length=120), nullable=True))
        if "expires_at" not in user_columns:
            op.add_column("users", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    tenant_indexes = _index_names(inspector, "tenants")
    if "ix_tenants_is_test" not in tenant_indexes:
        op.create_index("ix_tenants_is_test", "tenants", ["is_test"], unique=False)
    if "ix_tenants_created_by_automation" not in tenant_indexes:
        op.create_index("ix_tenants_created_by_automation", "tenants", ["created_by_automation"], unique=False)
    if "ix_tenants_test_run_id" not in tenant_indexes:
        op.create_index("ix_tenants_test_run_id", "tenants", ["test_run_id"], unique=False)
    if "ix_tenants_expires_at" not in tenant_indexes:
        op.create_index("ix_tenants_expires_at", "tenants", ["expires_at"], unique=False)
    if "ix_tenants_tenant_type" not in tenant_indexes:
        op.create_index("ix_tenants_tenant_type", "tenants", ["tenant_type"], unique=False)

    user_indexes = _index_names(inspector, "users")
    if "ix_users_is_test" not in user_indexes:
        op.create_index("ix_users_is_test", "users", ["is_test"], unique=False)
    if "ix_users_created_by_automation" not in user_indexes:
        op.create_index("ix_users_created_by_automation", "users", ["created_by_automation"], unique=False)
    if "ix_users_test_run_id" not in user_indexes:
        op.create_index("ix_users_test_run_id", "users", ["test_run_id"], unique=False)
    if "ix_users_expires_at" not in user_indexes:
        op.create_index("ix_users_expires_at", "users", ["expires_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_indexes = _index_names(inspector, "users")
    for index_name in [
        "ix_users_expires_at",
        "ix_users_test_run_id",
        "ix_users_created_by_automation",
        "ix_users_is_test",
    ]:
        if index_name in user_indexes:
            op.drop_index(index_name, table_name="users")

    tenant_indexes = _index_names(inspector, "tenants")
    for index_name in [
        "ix_tenants_tenant_type",
        "ix_tenants_expires_at",
        "ix_tenants_test_run_id",
        "ix_tenants_created_by_automation",
        "ix_tenants_is_test",
    ]:
        if index_name in tenant_indexes:
            op.drop_index(index_name, table_name="tenants")

    if inspector.has_table("users"):
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        for column_name in ["expires_at", "test_run_id", "created_by_automation", "is_test"]:
            if column_name in user_columns:
                op.drop_column("users", column_name)

    if inspector.has_table("tenants"):
        tenant_columns = {column["name"] for column in inspector.get_columns("tenants")}
        for column_name in ["expires_at", "test_run_id", "created_by_automation", "is_test", "tenant_type"]:
            if column_name in tenant_columns:
                op.drop_column("tenants", column_name)

    TENANT_TYPE_ENUM.drop(bind, checkfirst=True)
