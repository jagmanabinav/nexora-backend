from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampedModel


class UsageRecord(TimestampedModel):
    """Track resource usage for metering"""
    
    __tablename__ = "usage_records"
    __allow_unmapped__ = True
    
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    
    # Usage metrics
    metric_name = Column(String(100), nullable=False, index=True)  # api_calls, storage_gb, users, etc.
    metric_value = Column(Float, nullable=False, default=0.0)
    
    # Billing period
    billing_period_start = Column(DateTime, nullable=False, index=True)
    billing_period_end = Column(DateTime, nullable=False)
    
    # Metadata
    description = Column(String(500), nullable=True)
    source = Column(String(50), nullable=False, default="system")  # system, webhook, manual
    
    # Relationships
    tenant = relationship("Tenant")
    subscription = relationship("Subscription")
    
    __table_args__ = (
        Index("idx_tenant_metric_period", "tenant_id", "metric_name", "billing_period_start"),
    )
    
    def __repr__(self):
        return f"<UsageRecord(id={self.id}, metric={self.metric_name}, value={self.metric_value})>"
