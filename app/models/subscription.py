from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Enum as SQLEnum, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum
from app.models.base import Base, TimestampedModel


class BillingCycle(str, Enum):
    """Billing cycle options"""
    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    TRIAL = "trial"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class Subscription(TimestampedModel):
    """Tenant subscription to a billing plan"""
    
    __tablename__ = "subscriptions"
    __allow_unmapped__ = True
    
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("plans.id"), nullable=False, index=True)
    
    status = Column(
        SQLEnum(SubscriptionStatus, values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
        default=SubscriptionStatus.TRIAL,
        index=True,
    )
    billing_cycle = Column(
        SQLEnum(BillingCycle, values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
        default=BillingCycle.MONTHLY,
    )
    
    # Subscription details
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Pricing
    monthly_price = Column(Float, nullable=False, default=0.0)
    annual_price = Column(Float, nullable=False, default=0.0)
    setup_fee_paid = Column(Boolean, nullable=False, default=False)
    
    # Usage tracking
    current_usage_gb = Column(Float, nullable=False, default=0.0)
    current_api_calls = Column(Integer, nullable=False, default=0)
    current_user_count = Column(Integer, nullable=False, default=0)
    
    # Payment details
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    payment_method_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("payment_methods.id"), nullable=True)
    
    # Auto-renewal
    auto_renew = Column(Boolean, nullable=False, default=True)
    next_renewal_date = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")
    plan = relationship("Plan")
    payment_method = relationship("PaymentMethod")
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, tenant_id={self.tenant_id}, status={self.status})>"
    
    def is_active(self) -> bool:
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
    
    def is_trial(self) -> bool:
        return self.status == SubscriptionStatus.TRIAL
    
    def days_until_renewal(self) -> int:
        if self.current_period_end:
            period_end = self.current_period_end
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)
            delta = period_end - datetime.now(timezone.utc)
            return max(0, delta.days)
        return 0
