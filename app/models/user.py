"""User model."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE

from app.core.constants import USER_STATUS_ACTIVE
from app.models.base import TimestampedModel


class User(TimestampedModel):
    """User model representing platform users."""

    __tablename__ = "users"
    __allow_unmapped__ = True

    tenant_id: UUID = Column(
        UUID_TYPE(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: str = Column(String(255), nullable=False, index=True)
    password_hash: str = Column(String(255), nullable=False)
    first_name: Optional[str] = Column(String(255), nullable=True)
    last_name: Optional[str] = Column(String(255), nullable=True)
    phone: Optional[str] = Column(String(20), nullable=True)
    status: str = Column(String(50), default=USER_STATUS_ACTIVE, nullable=False)
    email_verified: bool = Column(Boolean, default=False, nullable=False)
    last_login_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tenant_id={self.tenant_id})>"
