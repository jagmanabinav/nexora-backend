from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, Text, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampedModel


class PaymentMethod(TimestampedModel):
    """Payment method for billing (Stripe integration)"""
    
    __tablename__ = "payment_methods"
    __allow_unmapped__ = True
    
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Payment method details (stored via Stripe, not raw cards)
    stripe_payment_method_id = Column(String(255), nullable=False, unique=True)
    stripe_customer_id = Column(String(255), nullable=False, index=True)
    
    # Display info
    payment_type = Column(String(50), nullable=False)  # card, bank_account, etc.
    card_brand = Column(String(50), nullable=True)  # visa, mastercard, amex, etc.
    card_last_4 = Column(String(4), nullable=True)
    card_exp_month = Column(String(2), nullable=True)
    card_exp_year = Column(String(4), nullable=True)
    
    # Bank account details (if applicable)
    bank_account_last_4 = Column(String(4), nullable=True)
    bank_account_holder_name = Column(String(255), nullable=True)
    
    # Usage
    is_default = Column(Boolean, nullable=False, default=False, index=True)
    is_valid = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Metadata
    description = Column(String(500), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")
    
    __table_args__ = (
        Index("idx_tenant_default_method", "tenant_id", "is_default"),
    )
    
    def __repr__(self):
        return f"<PaymentMethod(id={self.id}, type={self.payment_type}, is_default={self.is_default})>"
    
    def display_name(self) -> str:
        if self.payment_type == "card":
            return f"{self.card_brand or 'Card'} ending in {self.card_last_4}"
        elif self.payment_type == "bank_account":
            return f"Bank account ending in {self.bank_account_last_4}"
        return "Payment Method"
