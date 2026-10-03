"""Tenant repository for data access."""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.tenant import Tenant


class TenantRepository:
    """Repository for tenant data access."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        return self.db.query(Tenant).filter(Tenant.slug == slug).first()

    def create(self, name: str, slug: str, email: Optional[str] = None, phone: Optional[str] = None) -> Tenant:
        """Create a new tenant."""
        tenant = Tenant(name=name, slug=slug, email=email, phone=phone)
        self.db.add(tenant)
        self.db.flush()
        return tenant

    def update(self, tenant_id: UUID, **kwargs) -> Optional[Tenant]:
        """Update tenant."""
        tenant = self.get_by_id(tenant_id)
        if not tenant:
            return None
        for key, value in kwargs.items():
            if hasattr(tenant, key) and value is not None:
                setattr(tenant, key, value)
        self.db.flush()
        return tenant

    def delete(self, tenant_id: UUID) -> bool:
        """Delete tenant."""
        tenant = self.get_by_id(tenant_id)
        if not tenant:
            return False
        self.db.delete(tenant)
        return True

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """List all tenants."""
        return self.db.query(Tenant).offset(skip).limit(limit).all()

    def count(self) -> int:
        """Count total tenants."""
        return self.db.query(Tenant).count()
