"""
Role service for business logic.

Manages role operations and permissions assignment.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.role import RoleRepository
from app.repositories.permission import PermissionRepository
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.core.exceptions import ResourceNotFoundException, ValidationException
from uuid import uuid4


class RoleService:
    """Service for role management."""

    def __init__(self, session: Session):
        self.session = session
        self.role_repo = RoleRepository(session)
        self.permission_repo = PermissionRepository(session)

    def create_role(
        self, tenant_id: str, name: str, description: Optional[str] = None
    ) -> Role:
        """Create a new role."""
        # Check for duplicate name
        existing = self.role_repo.get_by_name(tenant_id, name)
        if existing:
            raise ValidationException(f"Role '{name}' already exists in this tenant")

        role = self.role_repo.create(tenant_id, name, description)
        self.session.commit()
        return role

    def list_roles(self, tenant_id: str, status: Optional[str] = None) -> List[Role]:
        """List all roles for a tenant."""
        return self.role_repo.list_by_tenant(tenant_id, status)

    def get_role(self, role_id: str, tenant_id: str) -> Role:
        """Get a single role with full details."""
        role = self.role_repo.get_by_id(role_id, tenant_id)
        if not role:
            raise ResourceNotFoundException(f"Role not found")
        return role

    def update_role(
        self, role_id: str, tenant_id: str, name: Optional[str] = None, description: Optional[str] = None
    ) -> Role:
        """Update role details."""
        role = self.role_repo.get_by_id(role_id, tenant_id)
        if not role:
            raise ResourceNotFoundException(f"Role not found")

        # Check for duplicate name if changing
        if name and name != role.name:
            existing = self.role_repo.get_by_name(tenant_id, name)
            if existing:
                raise ValidationException(f"Role '{name}' already exists in this tenant")

        role = self.role_repo.update(role_id, tenant_id, name=name, description=description)
        self.session.commit()
        return role

    def delete_role(self, role_id: str, tenant_id: str) -> None:
        """Delete a role."""
        self.role_repo.delete(role_id, tenant_id)
        self.session.commit()

    def add_permission_to_role(self, role_id: str, permission_id: str, tenant_id: str) -> Role:
        """Add a permission to a role."""
        role = self.role_repo.get_by_id(role_id, tenant_id)
        if not role:
            raise ResourceNotFoundException("Role not found")

        permission = self.permission_repo.get_by_id(permission_id)
        if not permission:
            raise ResourceNotFoundException("Permission not found")

        # Check if already added
        existing = (
            self.session.query(RolePermission)
            .filter(
                (RolePermission.role_id == role_id)
                & (RolePermission.permission_id == permission_id)
            )
            .first()
        )

        if not existing:
            role_permission = RolePermission(
                id=uuid4(),
                role_id=role_id,
                permission_id=permission_id,
            )
            self.session.add(role_permission)
            self.session.flush()

        self.session.commit()
        return role

    def remove_permission_from_role(self, role_id: str, permission_id: str, tenant_id: str) -> Role:
        """Remove a permission from a role."""
        role = self.role_repo.get_by_id(role_id, tenant_id)
        if not role:
            raise ResourceNotFoundException("Role not found")

        self.session.query(RolePermission).filter(
            (RolePermission.role_id == role_id)
            & (RolePermission.permission_id == permission_id)
        ).delete()
        self.session.flush()

        self.session.commit()
        return role

    def get_role_permissions(self, role_id: str, tenant_id: str) -> List[Permission]:
        """Get all permissions for a role."""
        role = self.role_repo.get_by_id(role_id, tenant_id)
        if not role:
            raise ResourceNotFoundException("Role not found")

        return role.permissions

    def set_role_permissions(
        self, role_id: str, tenant_id: str, permission_ids: List[str]
    ) -> Role:
        """Set all permissions for a role (replaces existing)."""
        role = self.role_repo.get_by_id(role_id, tenant_id)
        if not role:
            raise ResourceNotFoundException("Role not found")

        # Delete existing permissions
        self.session.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        self.session.flush()

        # Add new permissions
        for permission_id in permission_ids:
            permission = self.permission_repo.get_by_id(permission_id)
            if not permission:
                raise ResourceNotFoundException(f"Permission not found")

            role_permission = RolePermission(
                id=uuid4(),
                role_id=role_id,
                permission_id=permission_id,
            )
            self.session.add(role_permission)

        self.session.flush()
        self.session.commit()
        return role
