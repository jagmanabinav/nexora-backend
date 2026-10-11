"""GST calculation and issuance for FabWash invoices."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.models.fabwash_invoice import FabWashInvoice
from app.models.tenant import Tenant
from app.repositories.tenant import TenantRepository
from app.schemas.fabwash_invoice import FabWashInvoiceCreate

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


class FabWashInvoiceService:
    def __init__(self, session: Session):
        self.session = session

    def list_for_tenant(self, tenant_id: UUID) -> list[FabWashInvoice]:
        return (
            self.session.query(FabWashInvoice)
            .filter(FabWashInvoice.tenant_id == tenant_id)
            .order_by(FabWashInvoice.invoice_date.desc(), FabWashInvoice.invoice_number.desc())
            .all()
        )

    def get_for_tenant(self, invoice_id: UUID, tenant_id: UUID) -> FabWashInvoice:
        invoice = (
            self.session.query(FabWashInvoice)
            .filter(
                FabWashInvoice.id == invoice_id,
                FabWashInvoice.tenant_id == tenant_id,
            )
            .first()
        )
        if invoice is None:
            raise ResourceNotFoundException("Invoice not found")
        return invoice

    def issue(self, tenant_id: UUID, request: FabWashInvoiceCreate) -> FabWashInvoice:
        tenant = (
            self.session.query(Tenant)
            .filter(Tenant.id == tenant_id)
            .with_for_update()
            .one_or_none()
        )
        if tenant is None:
            raise ResourceNotFoundException("Tenant not found")

        financial_year = self._financial_year(request.invoice_date)
        prefix = f"FW/{financial_year}/"
        count = (
            self.session.query(FabWashInvoice)
            .filter(
                FabWashInvoice.tenant_id == tenant_id,
                FabWashInvoice.invoice_number.like(f"{prefix}%"),
            )
            .count()
        )
        invoice_number = f"{prefix}{count + 1:05d}"
        intra_state = request.seller.state_code == request.place_of_supply_code

        line_items: list[dict[str, Any]] = []
        taxable_total = Decimal("0")
        cgst_total = Decimal("0")
        sgst_total = Decimal("0")
        igst_total = Decimal("0")

        for item in request.line_items:
            taxable = money(item.quantity * item.rate)
            gst = money(taxable * item.gst_rate / Decimal("100"))
            cgst = money(gst / 2) if intra_state else Decimal("0.00")
            sgst = gst - cgst if intra_state else Decimal("0.00")
            igst = Decimal("0.00") if intra_state else gst
            taxable_total += taxable
            cgst_total += cgst
            sgst_total += sgst
            igst_total += igst
            line_items.append(
                {
                    "description": item.description,
                    "sac": item.sac,
                    "quantity": str(item.quantity),
                    "unit": item.unit,
                    "rate": str(money(item.rate)),
                    "gst_rate": str(item.gst_rate),
                    "taxable_value": str(taxable),
                    "cgst_amount": str(cgst),
                    "sgst_amount": str(sgst),
                    "igst_amount": str(igst),
                }
            )

        taxable_total = money(taxable_total)
        cgst_total = money(cgst_total)
        sgst_total = money(sgst_total)
        igst_total = money(igst_total)
        gst_total = money(cgst_total + sgst_total + igst_total)
        invoice = FabWashInvoice(
            tenant_id=tenant_id,
            invoice_number=invoice_number,
            invoice_date=request.invoice_date,
            due_date=request.due_date,
            status="issued",
            seller=json.loads(request.seller.model_dump_json()),
            buyer=json.loads(request.buyer.model_dump_json()),
            place_of_supply=request.place_of_supply,
            place_of_supply_code=request.place_of_supply_code,
            supply_type="intra-state" if intra_state else "inter-state",
            reverse_charge="yes" if request.reverse_charge else "no",
            line_items=line_items,
            taxable_value=taxable_total,
            cgst_amount=cgst_total,
            sgst_amount=sgst_total,
            igst_amount=igst_total,
            total_gst=gst_total,
            invoice_total=money(taxable_total + gst_total),
            reference=request.reference,
            notes=request.notes,
        )
        self.session.add(invoice)
        self.session.flush()
        return invoice

    @staticmethod
    def _financial_year(invoice_date: date) -> str:
        start_year = invoice_date.year if invoice_date.month >= 4 else invoice_date.year - 1
        return f"{start_year}-{str(start_year + 1)[-2:]}"
