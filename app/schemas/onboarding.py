"""Schemas for public tenant application signup and Super Admin review."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator
from typing import Annotated


class TenantApplicationCreate(BaseModel):
    application_code: Literal["fabwash"] = "fabwash"
    company_name: Annotated[str, StringConstraints(min_length=2, max_length=255)]
    company_slug: Annotated[
        str, StringConstraints(min_length=2, max_length=255, pattern="^[a-z0-9-]+$")
    ]
    company_email: Optional[EmailStr] = None
    company_phone: Optional[str] = Field(None, max_length=20)
    owner_email: EmailStr
    owner_password: str = Field(..., min_length=8, max_length=255)
    owner_first_name: Optional[Annotated[str, StringConstraints(max_length=255)]] = None
    owner_last_name: Optional[Annotated[str, StringConstraints(max_length=255)]] = None
    plan_id: UUID
    billing_cycle: Literal["monthly", "annual", "lifetime"] = "monthly"

    @field_validator("owner_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        return value


class TenantApplicationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    company_name: str
    company_slug: str
    company_email: Optional[str]
    company_phone: Optional[str]
    owner_email: str
    owner_first_name: Optional[str]
    owner_last_name: Optional[str]
    application_code: str
    plan_id: UUID
    plan_name: str
    plan_max_users: int
    monthly_price: float
    annual_price: float
    billing_cycle: str
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]


class TenantApplicationDecision(BaseModel):
    rejection_reason: Optional[str] = Field(None, max_length=2000)
