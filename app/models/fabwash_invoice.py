"""Tenant-issued FabWash GST invoices."""

from sqlalchemy import Column, Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as UUID_TYPE

from app.models.base import TimestampedModel


class FabWashInvoice(TimestampedModel):
    __tablename__ = "fabwash_invoices"

    tenant_id = Column(
        UUID_TYPE(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_number = Column(String(32), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="issued")
    seller = Column(JSONB, nullable=False)
    buyer = Column(JSONB, nullable=False)
    place_of_supply = Column(String(100), nullable=False)
    place_of_supply_code = Column(String(2), nullable=False)
    supply_type = Column(String(20), nullable=False)
    reverse_charge = Column(String(3), nullable=False, default="no")
    line_items = Column(JSONB, nullable=False)
    taxable_value = Column(Numeric(14, 2), nullable=False)
    cgst_amount = Column(Numeric(14, 2), nullable=False)
    sgst_amount = Column(Numeric(14, 2), nullable=False)
    igst_amount = Column(Numeric(14, 2), nullable=False)
    total_gst = Column(Numeric(14, 2), nullable=False)
    invoice_total = Column(Numeric(14, 2), nullable=False)
    reference = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "invoice_number", name="uq_fabwash_invoice_tenant_number"
        ),
    )
