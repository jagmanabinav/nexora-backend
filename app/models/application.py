"""
Application model for SaaS application registry.

Represents a registered application that can be managed by tenants.
Each application has its own API keys, webhooks, and OAuth providers.
"""

from uuid import uuid4
from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampedModel


class Application(TimestampedModel):
    """Application model with tenant scoping."""

    __tablename__ = "applications"
    __allow_unmapped__ = True

    id = Column(UUID_TYPE(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="draft", nullable=False)  # draft, active, suspended, archived
    webhook_url = Column(String(500), nullable=True)
    configuration = Column(Text, nullable=True)  # JSON for extension

    # Relationships
    tenant = relationship("Tenant")
    api_keys = relationship("APIKey", cascade="all, delete-orphan")
    oauth_providers = relationship("OAuthProvider", cascade="all, delete-orphan")

    # Unique constraint: name per tenant
    __table_args__ = (Index("idx_tenant_app_name", "tenant_id", "name", unique=True),)

    def __repr__(self) -> str:
        return f"<Application {self.name} for tenant {self.tenant_id}>"
