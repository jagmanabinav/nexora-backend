from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    Boolean,
    Enum as SQLEnum,
    UniqueConstraint,
)
from enum import Enum
from app.models.base import Base, TimestampedModel


class PlanTier(str, Enum):
    """Pricing plan tiers"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Plan(TimestampedModel):
    """Pricing plans available to tenants"""
    
    __tablename__ = "plans"
    __allow_unmapped__ = True
    
    name = Column(String(255), nullable=False)
    slug = Column(String(50), nullable=False)
    application_code = Column(String(100), nullable=False, default="nexora", index=True)
    tier = Column(
        SQLEnum(PlanTier, values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=True)
    
    # Pricing (INR)
    monthly_price = Column(Float, nullable=False, default=0.0)
    annual_price = Column(Float, nullable=False, default=0.0)
    setup_fee = Column(Float, nullable=False, default=0.0)
    
    # Limits
    max_users = Column(Integer, nullable=False, default=-1)  # -1 = unlimited
    max_api_keys = Column(Integer, nullable=False, default=-1)
    max_applications = Column(Integer, nullable=False, default=-1)
    storage_gb = Column(Integer, nullable=False, default=-1)  # -1 = unlimited
    api_requests_per_month = Column(Integer, nullable=False, default=-1)
    
    # Features
    support_level = Column(String(50), nullable=False, default="community")  # community, email, priority
    sso_enabled = Column(Boolean, nullable=False, default=False)
    advanced_analytics = Column(Boolean, nullable=False, default=False)
    webhook_support = Column(Boolean, nullable=False, default=False)
    custom_domain = Column(Boolean, nullable=False, default=False)
    api_access = Column(Boolean, nullable=False, default=False)
    
    # Metadata
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_default = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("application_code", "name", name="uq_plans_application_name"),
        UniqueConstraint("application_code", "slug", name="uq_plans_application_slug"),
    )
    
    def __repr__(self):
        return f"<Plan(id={self.id}, name={self.name}, tier={self.tier})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "application_code": self.application_code,
            "tier": self.tier,
            "description": self.description,
            "monthly_price": self.monthly_price,
            "annual_price": self.annual_price,
            "setup_fee": self.setup_fee,
            "max_users": self.max_users,
            "max_api_keys": self.max_api_keys,
            "max_applications": self.max_applications,
            "storage_gb": self.storage_gb,
            "api_requests_per_month": self.api_requests_per_month,
            "support_level": self.support_level,
            "sso_enabled": self.sso_enabled,
            "advanced_analytics": self.advanced_analytics,
            "webhook_support": self.webhook_support,
            "custom_domain": self.custom_domain,
            "api_access": self.api_access,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
