"""Add document extraction and OCR/AI processing tables.

Revision ID: 20260727_0006
Revises: 20260725_0005
Create Date: 2026-07-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260727_0006'
down_revision = '20260725_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DocumentExtraction table
    op.create_table(
        'document_extractions',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('intake_item_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False, server_default='unknown'),
        sa.Column('document_type_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('is_multi_document', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('company_name', sa.String(255), nullable=False, server_default=''),
        sa.Column('company_name_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('company_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('ticket_number', sa.String(120), nullable=False, server_default=''),
        sa.Column('ticket_number_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('invoice_number', sa.String(120), nullable=False, server_default=''),
        sa.Column('invoice_number_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('job_number', sa.String(120), nullable=False, server_default=''),
        sa.Column('job_number_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('ticket_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ticket_date_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('start_time_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('finish_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finish_time_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('total_hours_calculated', sa.Numeric(10, 2), nullable=True),
        sa.Column('customer_name', sa.String(255), nullable=False, server_default=''),
        sa.Column('customer_name_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('customer_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('project_name', sa.String(255), nullable=False, server_default=''),
        sa.Column('project_name_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('project_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('job_location', sa.String(255), nullable=False, server_default=''),
        sa.Column('job_location_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('driver_name', sa.String(255), nullable=False, server_default=''),
        sa.Column('driver_name_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('driver_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('driver_signature_present', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('truck_number', sa.String(120), nullable=False, server_default=''),
        sa.Column('truck_number_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('truck_type', sa.String(50), nullable=False, server_default=''),
        sa.Column('truck_type_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('material', sa.String(120), nullable=False, server_default=''),
        sa.Column('material_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('material_category', sa.String(50), nullable=False, server_default=''),
        sa.Column('origin', sa.String(255), nullable=False, server_default=''),
        sa.Column('origin_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('destination', sa.String(255), nullable=False, server_default=''),
        sa.Column('destination_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('load_count', sa.Integer(), nullable=True),
        sa.Column('load_count_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('weight_net_lbs', sa.Numeric(12, 2), nullable=True),
        sa.Column('weight_net_lbs_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('tons', sa.Numeric(12, 2), nullable=True),
        sa.Column('cubic_yards', sa.Numeric(12, 2), nullable=True),
        sa.Column('cubic_yards_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('rate_per_ton', sa.Numeric(10, 2), nullable=True),
        sa.Column('rate_per_load', sa.Numeric(10, 2), nullable=True),
        sa.Column('invoice_total', sa.Numeric(14, 2), nullable=True),
        sa.Column('invoice_total_confidence', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('status', sa.String(30), nullable=False, server_default='uploaded'),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('approved_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=False, server_default=''),
        sa.Column('distributed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ticket_created_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('ocr_raw_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('extracted_notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['intake_item_id'], ['intake_items.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['ticket_created_id'], ['tickets.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_extractions_status'), 'document_extractions', ['status'], unique=False)
    op.create_index(op.f('ix_document_extractions_tenant_id'), 'document_extractions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_document_extractions_intake_item_id'), 'document_extractions', ['intake_item_id'], unique=False)

    # ExtractionIssue table
    op.create_table(
        'extraction_issues',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('extraction_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('issue_type', sa.String(50), nullable=False),
        sa.Column('field_name', sa.String(120), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='warning'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('suggested_value', sa.Text(), nullable=False, server_default=''),
        sa.Column('correction_source', sa.String(120), nullable=False, server_default=''),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_value', sa.Text(), nullable=False, server_default=''),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['extraction_id'], ['document_extractions.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_extraction_issues_extraction_id'), 'extraction_issues', ['extraction_id'], unique=False)
    op.create_index(op.f('ix_extraction_issues_tenant_id'), 'extraction_issues', ['tenant_id'], unique=False)

    # Add extraction_id FK to tickets table
    op.add_column('tickets', sa.Column('extraction_id', postgresql.UUID(as_uuid=False), nullable=True))
    op.create_foreign_key(op.f('fk_tickets_extraction_id_document_extractions'), 'tickets', 'document_extractions', ['extraction_id'], ['id'])


def downgrade() -> None:
    # Drop FK from tickets to document_extractions
    op.drop_constraint(op.f('fk_tickets_extraction_id_document_extractions'), 'tickets', type_='foreignkey')
    op.drop_column('tickets', 'extraction_id')
    
    # Drop extraction_issues table
    op.drop_index(op.f('ix_extraction_issues_tenant_id'), table_name='extraction_issues')
    op.drop_index(op.f('ix_extraction_issues_extraction_id'), table_name='extraction_issues')
    op.drop_table('extraction_issues')
    
    # Drop document_extractions table
    op.drop_index(op.f('ix_document_extractions_intake_item_id'), table_name='document_extractions')
    op.drop_index(op.f('ix_document_extractions_tenant_id'), table_name='document_extractions')
    op.drop_index(op.f('ix_document_extractions_status'), table_name='document_extractions')
    op.drop_table('document_extractions')
