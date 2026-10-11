"""Schemas for tenant-issued FabWash GST invoices."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from typing import Annotated


class GstParty(BaseModel):
    name: Annotated[str, StringConstraints(min_length=2, max_length=255)]
    address: Annotated[str, StringConstraints(min_length=5, max_length=1000)]
    gstin: Optional[Annotated[str, StringConstraints(pattern=r"^\d{2}[A-Z0-9]{13}$")]] = None
    state: Annotated[str, StringConstraints(min_length=2, max_length=100)]
    state_code: Annotated[str, StringConstraints(pattern=r"^\d{2}$")]
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=30)

    @field_validator("gstin", mode="before")
    @classmethod
    def uppercase_gstin(cls, value: str) -> str:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("state_code")
    @classmethod
    def gstin_matches_state(cls, value: str, info):
        gstin = info.data.get("gstin")
        if gstin and gstin[:2] != value:
            raise ValueError("GSTIN state prefix must match the state code")
        return value


class GstInvoiceLineItem(BaseModel):
    description: Annotated[str, StringConstraints(min_length=2, max_length=500)]
    sac: Annotated[str, StringConstraints(pattern=r"^\d{4,8}$")]
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit: Annotated[str, StringConstraints(min_length=1, max_length=30)]
    rate: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    gst_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)


class FabWashInvoiceCreate(BaseModel):
    invoice_date: date
    due_date: date
    seller: GstParty
    buyer: GstParty
    place_of_supply: Annotated[str, StringConstraints(min_length=2, max_length=100)]
    place_of_supply_code: Annotated[str, StringConstraints(pattern=r"^\d{2}$")]
    reverse_charge: bool = False
    line_items: list[GstInvoiceLineItem] = Field(min_length=1, max_length=100)
    reference: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=4000)

    @field_validator("due_date")
    @classmethod
    def due_date_not_before_invoice(cls, value: date, info) -> date:
        invoice_date = info.data.get("invoice_date")
        if invoice_date and value < invoice_date:
            raise ValueError("Due date cannot be earlier than the invoice date")
        return value

    @model_validator(mode="after")
    def validate_supplier_registration(self):
        if not self.seller.gstin:
            raise ValueError("Supplier GSTIN is required")
        return self


class FabWashInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    invoice_number: str
    invoice_date: date
    due_date: date
    status: str
    seller: dict
    buyer: dict
    place_of_supply: str
    place_of_supply_code: str
    supply_type: str
    reverse_charge: str
    line_items: list[dict]
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_gst: Decimal
    invoice_total: Decimal
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
