"""Register FabWash in the platform applications catalog.

Revision ID: 011_fabwash_platform_app
Revises: 010_scope_plan_uniqueness
"""

from alembic import op


revision = "011_fabwash_platform_app"
down_revision = "010_scope_plan_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO applications (
            id, tenant_id, name, description, status, configuration,
            created_at, updated_at
        )
        SELECT
            'baf3a824-5f84-4dd4-b5ed-9326c4f8b6a1'::uuid,
            tenants.id,
            'FabWash',
            'Textile fabric washing and processing workspace.',
            'active',
            '{"product_code":"fabwash"}',
            now(),
            now()
        FROM tenants
        WHERE tenants.slug = 'nexora-platform'
          AND NOT EXISTS (
              SELECT 1 FROM applications
              WHERE applications.tenant_id = tenants.id
                AND applications.name = 'FabWash'
          )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM applications
        WHERE id = 'baf3a824-5f84-4dd4-b5ed-9326c4f8b6a1'::uuid
          AND name = 'FabWash'
          AND configuration = '{"product_code":"fabwash"}'
        """
    )
