"""
UserRole model for RBAC.

Junction table that assigns roles to users within a tenant.
A user can have multiple roles, and each assignment is tenant-scoped.
"""

from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampedModel


class UserRole(TimestampedModel):
    """UserRole junction table for tenant-scoped role assignment."""

    __tablename__ = "user_roles"
    __allow_unmapped__ = True

    id = Column(UUID_TYPE(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    user = relationship("User")
    role = relationship("Role")
    tenant = relationship("Tenant")

    # Ensure user and role belong to same tenant, and prevent duplicates
    __table_args__ = (
        Index("idx_tenant_user_role", "tenant_id", "user_id", "role_id", unique=True),
        Index("idx_user_roles", "user_id"),
        Index("idx_role_users", "role_id"),
    )

    def __repr__(self) -> str:
        return f"<UserRole user={self.user_id} role={self.role_id} tenant={self.tenant_id}>"
