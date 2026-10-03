from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampedModel


class EmailLog(TimestampedModel):
    """Track sent emails for audit and retry purposes"""
    
    __tablename__ = "email_logs"
    __allow_unmapped__ = True
    
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Email details
    to_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    template_name = Column(String(100), nullable=True)
    
    # Status tracking
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, sent, failed, bounced
    error_message = Column(Text, nullable=True)
    
    # Provider information
    provider = Column(String(50), nullable=False)  # smtp, sendgrid, mailgun
    provider_message_id = Column(String(255), nullable=True, unique=True)
    
    # Retry logic
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    last_retry_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    
    # Timestamps
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")
    
    __table_args__ = (
        Index("idx_tenant_status_date", "tenant_id", "status", "created_at"),
    )
    
    def __repr__(self):
        return f"<EmailLog(id={self.id}, to={self.to_email}, status={self.status})>"
