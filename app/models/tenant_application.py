"""Tenant application requests for access to Nexora products."""

from sqlalchemy import Column, ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy.orm import relationship

from app.models.base import TimestampedModel


class TenantApplication(TimestampedModel):
    """A company registration awaiting platform approval."""

    __tablename__ = "tenant_applications"
    __allow_unmapped__ = True

    tenant_id = Column(
        UUID_TYPE(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_plan_id = Column(
        UUID_TYPE(as_uuid=True),
        ForeignKey("plans.id"),
        nullable=False,
    )
    application_code = Column(String(100), nullable=False, default="fabwash")
    billing_cycle = Column(String(20), nullable=False, default="monthly")
    status = Column(String(20), nullable=False, default="pending", index=True)
    reviewed_by = Column(
        UUID_TYPE(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    tenant = relationship("Tenant")
    requested_plan = relationship("Plan")
    reviewer = relationship("User")
