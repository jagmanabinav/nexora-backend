"""
Permission model for RBAC.

Represents a specific permission that can be granted to roles.
Permissions are platform-wide (not tenant-scoped).
"""

from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, Text, Index

from app.models.base import Base, TimestampedModel


class Permission(TimestampedModel):
    """Permission model (platform-wide)."""

    __tablename__ = "permissions"
    __allow_unmapped__ = True

    id = Column(UUID_TYPE(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    __table_args__ = (Index("idx_permission_code", "code", unique=True),)

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"
