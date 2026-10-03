"""Tenant model."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.constants import TENANT_STATUS_ACTIVE
from app.models.base import TimestampedModel


class Tenant(TimestampedModel):
    """Tenant model representing organizations using the platform."""

    __tablename__ = "tenants"
    __allow_unmapped__ = True

    name: str = Column(String(255), nullable=False)
    slug: str = Column(String(255), unique=True, nullable=False, index=True)
    status: str = Column(String(50), default=TENANT_STATUS_ACTIVE, nullable=False)
    email: Optional[str] = Column(String(255), nullable=True)
    phone: Optional[str] = Column(String(20), nullable=True)
    configuration: dict = Column(JSONB, default={}, nullable=False)

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, status={self.status})>"
