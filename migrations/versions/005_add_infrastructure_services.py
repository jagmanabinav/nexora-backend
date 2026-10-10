"""Add infrastructure services tables

Revision ID: 005_add_infrastructure_services
Revises: 004_add_billing
Create Date: 2024-10-02 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '005_add_infrastructure_services'
down_revision = '004_add_billing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'email_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('to_email', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('template_name', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending', index=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_message_id', sa.String(255), nullable=True, unique=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tenant_status_date', 'email_logs', ['tenant_id', 'status', 'created_at'])

    op.create_table(
        'file_uploads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_key', sa.String(1000), nullable=False, unique=True),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('storage_provider', sa.String(50), nullable=False),
        sa.Column('bucket', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('md5_hash', sa.String(32), nullable=True),
        sa.Column('is_deleted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tenant_created_date', 'file_uploads', ['tenant_id', 'created_at'])
    op.create_index('idx_file_key', 'file_uploads', ['file_key'])


def downgrade() -> None:
    op.drop_table('file_uploads')
    op.drop_table('email_logs')
