"""
RolePermission model for RBAC.

Junction table that assigns permissions to roles.
A role can have multiple permissions.
"""

from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.models.base import Base


class RolePermission(Base):
    """RolePermission junction table."""

    __tablename__ = "role_permissions"
    __allow_unmapped__ = True

    id = Column(UUID_TYPE(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    role_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    role = relationship("Role")
    permission = relationship("Permission")

    # Prevent duplicate role-permission assignments
    __table_args__ = (Index("idx_role_permission", "role_id", "permission_id", unique=True),)

    def __repr__(self) -> str:
        return f"<RolePermission role={self.role_id} permission={self.permission_id}>"
