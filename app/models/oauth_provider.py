"""
OAuth Provider model for application OAuth configuration.

Stores OAuth provider credentials for applications.
Credentials are encrypted for security.
"""

from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampedModel


class OAuthProvider(TimestampedModel):
    """OAuth Provider model for application OAuth setup."""

    __tablename__ = "oauth_providers"

    id = Column(UUID_TYPE(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    application_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_name = Column(String(100), nullable=False)  # google, github, azure, etc.
    client_id = Column(String(255), nullable=False)
    client_secret = Column(String(255), nullable=False)  # Should be encrypted in production
    redirect_url = Column(String(500), nullable=True)
    scopes = Column(String(500), nullable=True)  # Comma-separated or JSON

    # Relationships
    application = relationship("Application")
    tenant = relationship("Tenant")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_app_oauth", "application_id"),
        Index("idx_tenant_oauth", "tenant_id"),
        Index("idx_provider_name", "application_id", "provider_name", unique=True),
    )

    def __repr__(self) -> str:
        return f"<OAuthProvider {self.provider_name} for app {self.application_id}>"
