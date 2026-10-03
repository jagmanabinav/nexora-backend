"""Add advanced features - webhooks, audit logs, data export

Revision ID: 006_add_advanced_features
Revises: 005_add_infrastructure_services
Create Date: 2024-10-02 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_advanced_features'
down_revision = '005_add_infrastructure_services'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create webhook_endpoints table
    op.create_table(
        'webhook_endpoints',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('secret', sa.String(256), nullable=False),
        sa.Column('events', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('retry_delay_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('headers', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_webhook_endpoints_tenant_active', 'webhook_endpoints', ['tenant_id', 'is_active'])
    op.create_index('idx_webhook_endpoints_url', 'webhook_endpoints', ['url'])
    
    # Create webhook_deliveries table
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('endpoint_id', sa.String(36), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_id', sa.String(36), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending', index=True),
        sa.Column('http_status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('last_attempted_at', sa.DateTime(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['endpoint_id'], ['webhook_endpoints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_webhook_deliveries_endpoint_status', 'webhook_deliveries', ['endpoint_id', 'status'])
    op.create_index('idx_webhook_deliveries_event', 'webhook_deliveries', ['event_type', 'event_id'])
    op.create_index('idx_webhook_deliveries_retry', 'webhook_deliveries', ['status', 'next_retry_at'])
    op.create_index('idx_webhook_deliveries_created', 'webhook_deliveries', ['created_at'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('actor_user_id', sa.String(36), nullable=True),
        sa.Column('actor_type', sa.String(50), nullable=False, server_default='user'),
        sa.Column('actor_ip', sa.String(45), nullable=True),
        sa.Column('actor_user_agent', sa.String(500), nullable=True),
        sa.Column('request_method', sa.String(10), nullable=True),
        sa.Column('request_path', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='success'),
        sa.Column('http_status_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_logs_tenant_created', 'audit_logs', ['tenant_id', 'created_at'])
    op.create_index('idx_audit_logs_resource', 'audit_logs', ['tenant_id', 'resource_type', 'resource_id'])
    op.create_index('idx_audit_logs_actor', 'audit_logs', ['tenant_id', 'actor_user_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_created', 'audit_logs', ['created_at'])
    
    # Create data_exports table
    op.create_table(
        'data_exports',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('format', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('include_users', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('include_subscriptions', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('include_invoices', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('include_audit_logs', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('include_usage_data', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('include_api_keys', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('include_webhook_events', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_from', sa.DateTime(), nullable=True),
        sa.Column('created_to', sa.DateTime(), nullable=True),
        sa.Column('requested_by', sa.String(36), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('download_token', sa.String(255), nullable=True),
        sa.Column('download_token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_downloaded_at', sa.DateTime(), nullable=True),
        sa.Column('total_records', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_data_exports_tenant_status', 'data_exports', ['tenant_id', 'status'])
    op.create_index('idx_data_exports_expires', 'data_exports', ['expires_at'])
    op.create_index('idx_data_exports_requested_by', 'data_exports', ['requested_by'])
    op.create_index('idx_data_exports_created', 'data_exports', ['created_at'])


def downgrade() -> None:
    # Drop indexes (Alembic drops them automatically with tables)
    
    # Drop tables in reverse order
    op.drop_table('data_exports')
    op.drop_table('audit_logs')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhook_endpoints')
