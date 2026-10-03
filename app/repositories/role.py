"""
Role repository for data access.

Provides tenant-scoped role management.
"""

from typing import List, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.role import Role
from app.core.exceptions import ResourceNotFoundException, ValidationException


class RoleRepository:
    """Repository for role data access with tenant scoping."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, tenant_id: str, name: str, description: Optional[str] = None) -> Role:
        """Create a new role for tenant."""
        role = Role(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            description=description,
            status="active",
        )
        self.session.add(role)
        self.session.flush()
        return role

    def get_by_id(self, role_id: str, tenant_id: str) -> Optional[Role]:
        """Get role by ID, scoped to tenant."""
        return self.session.query(Role).filter(
            and_(Role.id == role_id, Role.tenant_id == tenant_id)
        ).first()

    def get_by_name(self, tenant_id: str, name: str) -> Optional[Role]:
        """Get role by name, scoped to tenant."""
        return self.session.query(Role).filter(
            and_(Role.tenant_id == tenant_id, Role.name == name)
        ).first()

    def list_by_tenant(self, tenant_id: str, status: Optional[str] = None) -> List[Role]:
        """List all roles for tenant, optionally filtered by status."""
        query = self.session.query(Role).filter(Role.tenant_id == tenant_id)
        if status:
            query = query.filter(Role.status == status)
        return query.all()

    def update(self, role_id: str, tenant_id: str, **kwargs) -> Role:
        """Update role fields."""
        role = self.get_by_id(role_id, tenant_id)
        if not role:
            raise ResourceNotFoundException(f"Role {role_id} not found")

        for key, value in kwargs.items():
            if hasattr(role, key) and value is not None:
                setattr(role, key, value)

        self.session.flush()
        return role

    def delete(self, role_id: str, tenant_id: str) -> None:
        """Delete a role."""
        role = self.get_by_id(role_id, tenant_id)
        if not role:
            raise ResourceNotFoundException(f"Role {role_id} not found")

        self.session.delete(role)
        self.session.flush()

    def archive(self, role_id: str, tenant_id: str) -> Role:
        """Archive a role (soft delete)."""
        return self.update(role_id, tenant_id, status="archived")
