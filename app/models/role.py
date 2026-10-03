"""
Role model for RBAC.

Represents a role that can be assigned to users within a tenant.
Roles contain permissions that define what actions users can perform.
"""

from uuid import uuid4
from sqlalchemy import Column, String, Text, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampedModel


class Role(TimestampedModel):
    """Role model with tenant scoping and permissions."""

    __tablename__ = "roles"
    __allow_unmapped__ = True

    id = Column(UUID_TYPE(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)  # active, archived

    # Relationships
    tenant = relationship("Tenant")
    user_roles = relationship("UserRole", cascade="all, delete-orphan")
    permissions = relationship("Permission", secondary="role_permissions")

    # Unique constraint: name per tenant
    __table_args__ = (Index("idx_tenant_role_name", "tenant_id", "name", unique=True),)

    def __repr__(self) -> str:
        return f"<Role {self.name} for tenant {self.tenant_id}>"
