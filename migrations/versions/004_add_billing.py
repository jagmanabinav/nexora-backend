"""Add billing models and tables

Revision ID: 004_add_billing
Revises: 003_add_applications
Create Date: 2024-10-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '004_add_billing'
down_revision = '003_add_applications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('slug', sa.String(50), nullable=False, unique=True),
        sa.Column('tier', sa.Enum('free', 'starter', 'professional', 'enterprise', name='plantier'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('monthly_price', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('annual_price', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('setup_fee', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('max_users', sa.Integer(), nullable=False, server_default='-1'),
        sa.Column('max_api_keys', sa.Integer(), nullable=False, server_default='-1'),
        sa.Column('max_applications', sa.Integer(), nullable=False, server_default='-1'),
        sa.Column('storage_gb', sa.Integer(), nullable=False, server_default='-1'),
        sa.Column('api_requests_per_month', sa.Integer(), nullable=False, server_default='-1'),
        sa.Column('support_level', sa.String(50), nullable=False, server_default='community'),
        sa.Column('sso_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('advanced_analytics', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('webhook_support', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('custom_domain', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('api_access', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_plans_tier', 'plans', ['tier'])

    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('status', sa.Enum('active', 'trial', 'paused', 'cancelled', 'past_due', name='subscriptionstatus'), nullable=False, server_default='trial', index=True),
        sa.Column('billing_cycle', sa.Enum('monthly', 'annual', name='billingcycle'), nullable=False, server_default='monthly'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('monthly_price', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('annual_price', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('setup_fee_paid', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('current_usage_gb', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('current_api_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_user_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True, unique=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True, index=True),
        sa.Column('payment_method_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('next_renewal_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'payment_methods',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('stripe_payment_method_id', sa.String(255), nullable=False, unique=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=False, index=True),
        sa.Column('payment_type', sa.String(50), nullable=False),
        sa.Column('card_brand', sa.String(50), nullable=True),
        sa.Column('card_last_4', sa.String(4), nullable=True),
        sa.Column('card_exp_month', sa.String(2), nullable=True),
        sa.Column('card_exp_year', sa.String(4), nullable=True),
        sa.Column('bank_account_last_4', sa.String(4), nullable=True),
        sa.Column('bank_account_holder_name', sa.String(255), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tenant_default_method', 'payment_methods', ['tenant_id', 'is_default'])

    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('invoice_number', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('status', sa.Enum('draft', 'sent', 'pending', 'paid', 'failed', 'refunded', 'overdue', name='invoicestatus'), nullable=False, server_default='draft', index=True),
        sa.Column('issue_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subtotal', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('tax_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('discount_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('paid_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('line_items', sa.Text(), nullable=True),
        sa.Column('stripe_invoice_id', sa.String(255), nullable=True, unique=True),
        sa.Column('payment_method_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_trial_invoice', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id']),
        sa.ForeignKeyConstraint(['payment_method_id'], ['payment_methods.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('metric_name', sa.String(100), nullable=False, index=True),
        sa.Column('metric_value', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('billing_period_start', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('billing_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('source', sa.String(50), nullable=False, server_default='system'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tenant_metric_period', 'usage_records', ['tenant_id', 'metric_name', 'billing_period_start'])

    op.create_foreign_key(
        'fk_subscriptions_payment_method_id',
        'subscriptions',
        'payment_methods',
        ['payment_method_id'],
        ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_subscriptions_payment_method_id', 'subscriptions', type_='foreignkey')
    op.drop_table('payment_methods')
    op.drop_table('usage_records')
    op.drop_table('invoices')
    op.drop_table('subscriptions')
    op.drop_table('plans')
    op.execute("DROP TYPE IF EXISTS billingcycle CASCADE;")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus CASCADE;")
    op.execute("DROP TYPE IF EXISTS invoicestatus CASCADE;")
    op.execute("DROP TYPE IF EXISTS plantier CASCADE;")
