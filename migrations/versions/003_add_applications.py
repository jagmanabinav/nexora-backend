"""Add application registry tables (applications, api_keys, oauth_providers)

Revision ID: 003_add_applications
Revises: 002_add_rbac
Create Date: 2026-10-02 19:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_applications'
down_revision = '002_add_rbac'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create applications table
    op.create_table(
        'applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('webhook_url', sa.String(length=500), nullable=True),
        sa.Column('configuration', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_applications_tenant_id'), 'applications', ['tenant_id'])
    op.create_index('idx_tenant_app_name', 'applications', ['tenant_id', 'name'], unique=True)

    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_application_id'), 'api_keys', ['application_id'])
    op.create_index(op.f('ix_api_keys_tenant_id'), 'api_keys', ['tenant_id'])
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)

    # Create oauth_providers table
    op.create_table(
        'oauth_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_name', sa.String(length=100), nullable=False),
        sa.Column('client_id', sa.String(length=255), nullable=False),
        sa.Column('client_secret', sa.String(length=255), nullable=False),
        sa.Column('redirect_url', sa.String(length=500), nullable=True),
        sa.Column('scopes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_oauth_providers_application_id'), 'oauth_providers', ['application_id'])
    op.create_index(op.f('ix_oauth_providers_tenant_id'), 'oauth_providers', ['tenant_id'])
    op.create_index('idx_provider_name', 'oauth_providers', ['application_id', 'provider_name'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_provider_name', table_name='oauth_providers')
    op.drop_index(op.f('ix_oauth_providers_tenant_id'), table_name='oauth_providers')
    op.drop_index(op.f('ix_oauth_providers_application_id'), table_name='oauth_providers')
    op.drop_table('oauth_providers')

    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_tenant_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_application_id'), table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_index('idx_tenant_app_name', table_name='applications')
    op.drop_index(op.f('ix_applications_tenant_id'), table_name='applications')
    op.drop_table('applications')
