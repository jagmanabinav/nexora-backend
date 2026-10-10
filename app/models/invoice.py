from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from app.models.base import Base, TimestampedModel


class InvoiceStatus(str, Enum):
    """Invoice status"""
    DRAFT = "draft"
    SENT = "sent"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    OVERDUE = "overdue"


class Invoice(TimestampedModel):
    """Billing invoice for subscriptions"""
    
    __tablename__ = "invoices"
    __allow_unmapped__ = True
    
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    
    invoice_number = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(
        SQLEnum(InvoiceStatus, values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
        default=InvoiceStatus.DRAFT,
        index=True,
    )
    
    # Dates
    issue_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    
    # Amounts
    subtotal = Column(Float, nullable=False, default=0.0)
    tax_amount = Column(Float, nullable=False, default=0.0)
    discount_amount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)
    paid_amount = Column(Float, nullable=False, default=0.0)
    
    # Itemization
    description = Column(Text, nullable=True)
    line_items = Column(Text, nullable=True)  # JSON string
    
    # Payment tracking
    stripe_invoice_id = Column(String(255), nullable=True, unique=True)
    payment_method_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("payment_methods.id"), nullable=True)
    
    # Retry tracking
    retry_count = Column(Integer, nullable=False, default=0)
    last_retry_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    is_trial_invoice = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    tenant = relationship("Tenant")
    subscription = relationship("Subscription")
    payment_method = relationship("PaymentMethod")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number={self.invoice_number}, status={self.status})>"
    
    def is_overdue(self) -> bool:
        if self.status in [InvoiceStatus.PAID, InvoiceStatus.REFUNDED]:
            return False
        return datetime.utcnow() > self.due_date if self.due_date else False
    
    def remaining_balance(self) -> float:
        return max(0, self.total_amount - self.paid_amount)
    
    def can_retry(self) -> bool:
        return self.status in [InvoiceStatus.FAILED, InvoiceStatus.OVERDUE] and self.retry_count < 3
