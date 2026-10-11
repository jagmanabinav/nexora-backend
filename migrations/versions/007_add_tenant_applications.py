"""Add tenant product registration and approval requests.

Revision ID: 007_add_tenant_applications
Revises: 006_add_advanced_features
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "007_add_tenant_applications"
down_revision = "006_add_advanced_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_code", sa.String(length=100), nullable=False, server_default="fabwash"),
        sa.Column("billing_cycle", sa.String(length=20), nullable=False, server_default="monthly"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_plan_id"], ["plans.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_applications_tenant_id",
        "tenant_applications",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_tenant_applications_status",
        "tenant_applications",
        ["status"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description, created_at, updated_at)
            VALUES (
                gen_random_uuid(),
                'admin:tenant_application:review',
                'Review tenant application registrations',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id)
            SELECT
                gen_random_uuid(),
                super_admin_role.id,
                review_permission.id
            FROM roles AS super_admin_role
            JOIN role_permissions AS create_assignment
                ON create_assignment.role_id = super_admin_role.id
            JOIN permissions AS create_permission
                ON create_permission.id = create_assignment.permission_id
                AND create_permission.code = 'admin:plan:create'
            JOIN role_permissions AS update_assignment
                ON update_assignment.role_id = super_admin_role.id
            JOIN permissions AS update_permission
                ON update_permission.id = update_assignment.permission_id
                AND update_permission.code = 'admin:plan:update'
            CROSS JOIN permissions AS review_permission
            WHERE super_admin_role.name = 'Super Admin'
                AND review_permission.code = 'admin:tenant_application:review'
                AND NOT EXISTS (
                    SELECT 1
                    FROM role_permissions AS existing_assignment
                    WHERE existing_assignment.role_id = super_admin_role.id
                        AND existing_assignment.permission_id = review_permission.id
                )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_applications_status", table_name="tenant_applications")
    op.drop_index("ix_tenant_applications_tenant_id", table_name="tenant_applications")
    op.drop_table("tenant_applications")
