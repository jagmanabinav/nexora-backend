"""
API Key model for application authentication.

Each application can have multiple API keys for different integrations.
Keys are hashed for security and can be revoked.
"""

from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampedModel


class APIKey(TimestampedModel):
    """API Key model for application authentication."""

    __tablename__ = "api_keys"
    __allow_unmapped__ = True

    id = Column(UUID_TYPE(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    application_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)  # Hashed for security
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Relationships
    application = relationship("Application")
    tenant = relationship("Tenant")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_app_keys", "application_id"),
        Index("idx_tenant_keys", "tenant_id"),
        Index("idx_key_hash", "key_hash", unique=True),
    )

    def __repr__(self) -> str:
        return f"<APIKey {self.name} for app {self.application_id}>"
