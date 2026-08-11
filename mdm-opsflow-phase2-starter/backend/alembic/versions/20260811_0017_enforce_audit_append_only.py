"""Enforce append-only audit logs at database layer.

Revision ID: 20260811_0017
Revises: 20260811_0016
Create Date: 2026-08-11 23:59:00.000000
"""

from alembic import op


revision = "20260811_0017"
down_revision = "20260811_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_logs_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF current_setting('app.audit_retention_mode', true) = 'on' THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION 'audit_logs is append-only';
        END;
        $$;
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_prevent_audit_logs_update ON audit_logs;
        CREATE TRIGGER trg_prevent_audit_logs_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_logs_mutation();
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_prevent_audit_logs_delete ON audit_logs;
        CREATE TRIGGER trg_prevent_audit_logs_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_logs_mutation();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_logs_update ON audit_logs;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_logs_delete ON audit_logs;")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_logs_mutation();")
