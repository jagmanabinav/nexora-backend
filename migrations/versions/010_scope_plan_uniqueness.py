"""Allow plan names and slugs to be reused across applications.

Revision ID: 010_scope_plan_uniqueness
Revises: 009_application_scoped_plans
"""

from alembic import op
import sqlalchemy as sa


revision = "010_scope_plan_uniqueness"
down_revision = "009_application_scoped_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("plans_name_key", "plans", type_="unique")
    op.drop_constraint("plans_slug_key", "plans", type_="unique")
    op.create_unique_constraint(
        "uq_plans_application_name", "plans", ["application_code", "name"]
    )
    op.create_unique_constraint(
        "uq_plans_application_slug", "plans", ["application_code", "slug"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_plans_application_slug", "plans", type_="unique")
    op.drop_constraint("uq_plans_application_name", "plans", type_="unique")
    op.create_unique_constraint("plans_slug_key", "plans", ["slug"])
    op.create_unique_constraint("plans_name_key", "plans", ["name"])
