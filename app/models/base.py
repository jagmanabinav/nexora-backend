"""Base model for all database models."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class TimestampedModel(Base):
    """Base model with timestamp fields."""

    __abstract__ = True
    __allow_unmapped__ = True

    id: Mapped[UUID] = mapped_column(
        UUID_TYPE(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BaseTenantModel(TimestampedModel):
    """Base model with tenant isolation."""

    __abstract__ = True
    __allow_unmapped__ = True

    tenant_id: Mapped[UUID] = mapped_column(
        UUID_TYPE(as_uuid=True),
        nullable=False,
    )
