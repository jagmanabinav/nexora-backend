"""Refresh token model for token rotation and revocation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE

from app.models.base import TimestampedModel


class RefreshToken(TimestampedModel):
    """Refresh token model for managing token rotation and revocation."""

    __tablename__ = "refresh_tokens"
    __allow_unmapped__ = True

    user_id: UUID = Column(
        UUID_TYPE(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: UUID = Column(
        UUID_TYPE(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: str = Column(Text, nullable=False, unique=True, index=True)
    is_revoked: bool = Column(Boolean, default=False, nullable=False)
    expires_at: datetime = Column(DateTime(timezone=True), nullable=False)
    revoked_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, is_revoked={self.is_revoked})>"
