"""Configure FabWash plans and add lifetime billing cycles.

Revision ID: 008_fabwash_plans_and_lifetime
Revises: 007_add_tenant_applications
"""

from alembic import op


revision = "008_fabwash_plans_and_lifetime"
down_revision = "007_add_tenant_applications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE billingcycle ADD VALUE IF NOT EXISTS 'lifetime'")
    op.execute(
        """
        INSERT INTO plans (
            id, name, slug, tier, description,
            monthly_price, annual_price, setup_fee,
            max_users, max_api_keys, max_applications, storage_gb,
            api_requests_per_month, support_level, sso_enabled,
            advanced_analytics, webhook_support, custom_domain, api_access,
            is_active, is_default, display_order, created_at, updated_at
        ) VALUES
        (
            'a5e55312-37df-4ddd-a647-0040fbdcfd01',
            'FabWash Free - 1 Month', 'fabwash-free-month', 'free',
            'Free for one month. One manager account; the manager handles all work.',
            0, 0, 0, 1, -1, -1, -1, -1, 'community',
            false, false, false, false, false, true, true, 1, now(), now()
        ),
        (
            'a5e55312-37df-4ddd-a647-0040fbdcfd02',
            'FabWash Monthly', 'fabwash-monthly', 'starter',
            '399 INR per month. Includes one manager and one additional user.',
            399, 0, 0, 2, -1, -1, -1, -1, 'community',
            false, false, false, false, false, true, false, 2, now(), now()
        ),
        (
            'a5e55312-37df-4ddd-a647-0040fbdcfd03',
            'FabWash Lifetime', 'fabwash-lifetime', 'professional',
            'One-time lifetime plan payment of 9999 INR. Includes one manager and one additional user.',
            0, 0, 9999, 2, -1, -1, -1, -1, 'community',
            false, false, false, false, false, true, false, 3, now(), now()
        )
        ON CONFLICT (slug) DO UPDATE SET
            name = EXCLUDED.name,
            tier = EXCLUDED.tier,
            description = EXCLUDED.description,
            monthly_price = EXCLUDED.monthly_price,
            annual_price = EXCLUDED.annual_price,
            setup_fee = EXCLUDED.setup_fee,
            max_users = EXCLUDED.max_users,
            max_api_keys = EXCLUDED.max_api_keys,
            max_applications = EXCLUDED.max_applications,
            storage_gb = EXCLUDED.storage_gb,
            api_requests_per_month = EXCLUDED.api_requests_per_month,
            support_level = EXCLUDED.support_level,
            sso_enabled = EXCLUDED.sso_enabled,
            advanced_analytics = EXCLUDED.advanced_analytics,
            webhook_support = EXCLUDED.webhook_support,
            custom_domain = EXCLUDED.custom_domain,
            api_access = EXCLUDED.api_access,
            is_active = true,
            is_default = EXCLUDED.is_default,
            display_order = EXCLUDED.display_order,
            updated_at = now()
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE plans
        SET is_active = false, is_default = false, updated_at = now()
        WHERE slug IN (
            'fabwash-free-month',
            'fabwash-monthly',
            'fabwash-lifetime'
        )
        """
    )
