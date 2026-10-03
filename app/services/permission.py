"""
Permission service for business logic.

Manages platform-wide permissions and seeding.
"""

from typing import List
from sqlalchemy.orm import Session

from app.repositories.permission import PermissionRepository
from app.models.permission import Permission
from app.core.permissions import DEFAULT_PERMISSIONS, DEFAULT_ROLES, PermissionCode
from app.core.exceptions import ResourceNotFoundException


class PermissionService:
    """Service for permission management."""

    def __init__(self, session: Session):
        self.session = session
        self.permission_repo = PermissionRepository(session)

    def list_all_permissions(self) -> List[Permission]:
        """Get all available permissions."""
        return self.permission_repo.list_all()

    def get_permission(self, permission_id: str) -> Permission:
        """Get a single permission."""
        permission = self.permission_repo.get_by_id(permission_id)
        if not permission:
            raise ResourceNotFoundException("Permission not found")
        return permission

    def seed_permissions(self) -> None:
        """Seed default permissions into database."""
        for code, description in DEFAULT_PERMISSIONS.items():
            existing = self.permission_repo.get_by_code(code)
            if not existing:
                self.permission_repo.create(code, description)

        self.session.commit()
