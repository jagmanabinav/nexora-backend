"""Categorize billing plans by application.

Revision ID: 009_application_scoped_plans
Revises: 008_fabwash_plans_and_lifetime
"""

from alembic import op
import sqlalchemy as sa


revision = "009_application_scoped_plans"
down_revision = "008_fabwash_plans_and_lifetime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plans",
        sa.Column(
            "application_code",
            sa.String(length=100),
            nullable=False,
            server_default="nexora",
        ),
    )
    op.create_index(
        "ix_plans_application_code", "plans", ["application_code"], unique=False
    )
    op.execute(
        """
        UPDATE plans
        SET application_code = 'fabwash'
        WHERE slug IN (
            'fabwash-free-month',
            'fabwash-monthly',
            'fabwash-lifetime'
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_plans_application_code", table_name="plans")
    op.drop_column("plans", "application_code")
