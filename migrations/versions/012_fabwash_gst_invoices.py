"""Create tenant-scoped FabWash GST invoices.

Revision ID: 012_fabwash_gst_invoices
Revises: 011_fabwash_platform_app
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "012_fabwash_gst_invoices"
down_revision = "011_fabwash_platform_app"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fabwash_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(length=32), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("seller", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("buyer", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("place_of_supply", sa.String(length=100), nullable=False),
        sa.Column("place_of_supply_code", sa.String(length=2), nullable=False),
        sa.Column("supply_type", sa.String(length=20), nullable=False),
        sa.Column("reverse_charge", sa.String(length=3), nullable=False),
        sa.Column("line_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("taxable_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("cgst_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("sgst_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("igst_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_gst", sa.Numeric(14, 2), nullable=False),
        sa.Column("invoice_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "invoice_number",
            name="uq_fabwash_invoice_tenant_number",
        ),
    )
    op.create_index(
        "ix_fabwash_invoices_tenant_id",
        "fabwash_invoices",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_fabwash_invoices_tenant_id", table_name="fabwash_invoices")
    op.drop_table("fabwash_invoices")
