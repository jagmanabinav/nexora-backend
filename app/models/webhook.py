from enum import Enum
from uuid import uuid4
from sqlalchemy import String, Boolean, Integer, DateTime, Text, JSON, Enum as SQLEnum, ForeignKey, Index, Column
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from datetime import datetime, timezone

from app.models.base import Base, BaseTenantModel, TimestampedModel


class WebhookEventType(str, Enum):
    """Webhook event types"""
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_INVITED = "user.invited"
    
    # Subscription events
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    SUBSCRIPTION_RENEWED = "subscription.renewed"
    SUBSCRIPTION_UPGRADED = "subscription.upgraded"
    SUBSCRIPTION_DOWNGRADED = "subscription.downgraded"
    SUBSCRIPTION_PAUSED = "subscription.paused"
    SUBSCRIPTION_RESUMED = "subscription.resumed"
    
    # Invoice events
    INVOICE_CREATED = "invoice.created"
    INVOICE_PAID = "invoice.paid"
    INVOICE_FAILED = "invoice.failed"
    INVOICE_OVERDUE = "invoice.overdue"
    INVOICE_REFUNDED = "invoice.refunded"
    
    # Application events
    APPLICATION_CREATED = "application.created"
    APPLICATION_UPDATED = "application.updated"
    APPLICATION_DELETED = "application.deleted"
    
    # Custom events
    CUSTOM = "custom"


class WebhookEndpoint(BaseTenantModel):
    """Webhook endpoints for sending events to external systems"""
    
    __tablename__ = "webhook_endpoints"
    __allow_unmapped__ = True
    __table_args__ = (
        Index("idx_webhook_endpoints_tenant_active", "tenant_id", "is_active"),
        Index("idx_webhook_endpoints_url", "url"),
    )
    
    # Basic info
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    description = Column(String(1000), nullable=True)
    
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    secret = Column(String(256), nullable=False)  # HMAC secret for signature verification
    
    # Event filtering
    events = Column(JSON, default=list, nullable=False)  # List of event types to subscribe to
    
    # Retry configuration
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay_seconds = Column(Integer, default=300, nullable=False)  # 5 minutes
    
    # Metadata
    headers = Column(JSON, default=dict, nullable=False)  # Custom headers to include in requests
    
    # Relationships
    deliveries = relationship("WebhookDelivery", back_populates="endpoint", cascade="all, delete-orphan")
    
    # Indexes
    def should_deliver_event(self, event_type: str) -> bool:
        """Check if this endpoint should receive the event"""
        if not self.is_active:
            return False
        if not self.events:  # Empty events list means all events
            return True
        return event_type in self.events or "*" in self.events
    
    def get_signature(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature for payload"""
        import hmac
        import hashlib
        return hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()


class WebhookDelivery(Base):
    """Records of webhook delivery attempts"""
    
    __tablename__ = "webhook_deliveries"
    __allow_unmapped__ = True

    id = Column(UUID_TYPE(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    
    # Relationship
    endpoint_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False)
    endpoint = relationship("WebhookEndpoint", back_populates="deliveries")
    
    # Event info
    event_type = Column(String(100), nullable=False)
    event_id = Column(UUID_TYPE(as_uuid=True), nullable=False)  # Reference to the event that triggered delivery
    
    # Payload
    payload = Column(JSON, nullable=False)
    
    # Delivery status
    status = Column(String(50), default="pending", nullable=False)  # pending, sent, failed, exhausted
    http_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Retry tracking
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    last_attempted_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timing
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_webhook_deliveries_endpoint_status", "endpoint_id", "status"),
        Index("idx_webhook_deliveries_event", "event_type", "event_id"),
        Index("idx_webhook_deliveries_retry", "status", "next_retry_at"),
        Index("idx_webhook_deliveries_created", "created_at"),
    )
    
    def can_retry(self) -> bool:
        """Check if delivery can be retried"""
        return (
            self.status in ["pending", "failed"] and
            self.attempt_count < self.max_attempts
        )
    
    def mark_sent(self, http_status: int, response: str = None):
        """Mark delivery as successfully sent"""
        self.status = "sent"
        self.http_status_code = http_status
        self.response_body = response
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_failed(self, error: str, http_status: int = None):
        """Mark delivery as failed"""
        self.attempt_count += 1
        self.error_message = error
        self.http_status_code = http_status
        self.last_attempted_at = datetime.now(timezone.utc)
        
        if self.attempt_count >= self.max_attempts:
            self.status = "exhausted"
            self.completed_at = datetime.now(timezone.utc)
        else:
            self.status = "failed"
            # Exponential backoff: 5min, 30min, 2hr
            backoff_multiplier = 2 ** (self.attempt_count - 1)
            from datetime import timedelta
            self.next_retry_at = self.last_attempted_at + timedelta(
                seconds=self.endpoint.retry_delay_seconds * backoff_multiplier
            )
