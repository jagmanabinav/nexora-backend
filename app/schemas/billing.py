from pydantic import BaseModel, ConfigDict, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from uuid import UUID


class PlanTierEnum(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class BillingCycleEnum(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"
    LIFETIME = "lifetime"


class SubscriptionStatusEnum(str, Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class InvoiceStatusEnum(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    OVERDUE = "overdue"


# Plan Schemas
class PlanBase(BaseModel):
    name: str
    slug: str
    application_code: str = Field(default="nexora", min_length=1, max_length=100)
    tier: PlanTierEnum
    description: Optional[str] = None
    monthly_price: float = Field(ge=0)
    annual_price: float = Field(ge=0)
    setup_fee: float = Field(ge=0, default=0)
    max_users: int = -1
    max_api_keys: int = -1
    max_applications: int = -1
    storage_gb: int = -1
    api_requests_per_month: int = -1
    support_level: str = "community"
    sso_enabled: bool = False
    advanced_analytics: bool = False
    webhook_support: bool = False
    custom_domain: bool = False
    api_access: bool = False


class PlanCreate(PlanBase):
    is_active: bool = True
    is_default: bool = False
    display_order: int = 0


class PlanUpdate(BaseModel):
    slug: Optional[str] = None
    application_code: Optional[str] = Field(None, min_length=1, max_length=100)
    tier: Optional[PlanTierEnum] = None
    name: Optional[str] = None
    description: Optional[str] = None
    monthly_price: Optional[float] = None
    annual_price: Optional[float] = None
    setup_fee: Optional[float] = None
    max_users: Optional[int] = None
    max_api_keys: Optional[int] = None
    max_applications: Optional[int] = None
    storage_gb: Optional[int] = None
    api_requests_per_month: Optional[int] = None
    support_level: Optional[str] = None
    sso_enabled: Optional[bool] = None
    advanced_analytics: Optional[bool] = None
    webhook_support: Optional[bool] = None
    custom_domain: Optional[bool] = None
    api_access: Optional[bool] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    display_order: Optional[int] = None


class PlanResponse(PlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    is_default: bool
    display_order: int
    created_at: datetime
    updated_at: datetime
    
# Subscription Schemas
class SubscriptionBase(BaseModel):
    plan_id: str
    billing_cycle: BillingCycleEnum = BillingCycleEnum.MONTHLY
    trial_days: int = 14
    auto_renew: bool = True


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    plan_id: Optional[str] = None
    auto_renew: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plan_id: UUID
    status: SubscriptionStatusEnum
    billing_cycle: BillingCycleEnum
    current_period_start: datetime
    current_period_end: datetime
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    cancelled_at: Optional[datetime]
    monthly_price: float
    annual_price: float
    auto_renew: bool
    created_at: datetime
    updated_at: datetime
    
# Invoice Schemas
class InvoiceBase(BaseModel):
    subscription_id: str
    subtotal: float
    tax_amount: float = 0
    discount_amount: float = 0
    total_amount: float
    description: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    subscription_id: UUID
    invoice_number: str
    status: InvoiceStatusEnum
    issue_date: datetime
    due_date: datetime
    sent_at: Optional[datetime]
    paid_at: Optional[datetime]
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    paid_amount: float
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    
# Usage Record Schemas
class UsageRecordBase(BaseModel):
    metric_name: str
    metric_value: float = Field(ge=0)
    description: Optional[str] = None


class UsageRecordCreate(UsageRecordBase):
    pass


class UsageRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    subscription_id: UUID
    metric_name: str
    metric_value: float
    billing_period_start: datetime
    billing_period_end: datetime
    created_at: datetime
    
# Payment Method Schemas
class PaymentMethodBase(BaseModel):
    stripe_payment_method_id: str
    stripe_customer_id: str
    payment_type: str
    description: Optional[str] = None


class PaymentMethodCreate(PaymentMethodBase):
    pass


class PaymentMethodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    payment_type: str
    card_brand: Optional[str]
    card_last_4: Optional[str]
    card_exp_month: Optional[str]
    card_exp_year: Optional[str]
    bank_account_last_4: Optional[str]
    is_default: bool
    is_valid: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
# Complex Response Schemas
class BillingOverviewResponse(BaseModel):
    subscription: Optional[dict]
    pricing: Optional[dict]
    payment_method: Optional[dict]
    recent_invoices: List[dict]


class CurrentUsageResponse(BaseModel):
    subscription_id: Optional[UUID] = None
    plan_name: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    metrics: dict = Field(default_factory=dict)
    status: Optional[str] = None


class UpgradeSubscriptionRequest(BaseModel):
    new_plan_id: str
    proration_credits: Optional[float] = None


class DowngradeSubscriptionRequest(BaseModel):
    new_plan_id: str


class CancelSubscriptionRequest(BaseModel):
    reason: Optional[str] = None
    effective_immediately: bool = False


class PaymentRecordRequest(BaseModel):
    amount: float = Field(gt=0)
    payment_method: str = "stripe"


class TrackUsageRequest(BaseModel):
    metric_name: str
    amount: float = Field(gt=0)
    description: Optional[str] = None
