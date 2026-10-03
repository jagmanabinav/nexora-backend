"""
Permission repository for data access.

Provides access to platform-wide permissions.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.core.exceptions import ResourceNotFoundException
from uuid import uuid4


class PermissionRepository:
    """Repository for permission data access."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, code: str, description: Optional[str] = None) -> Permission:
        """Create a new permission."""
        permission_id = uuid4()
        permission = Permission(
            id=permission_id,
            code=code,
            description=description,
        )
        self.session.add(permission)
        self.session.flush()
        return permission

    def get_by_id(self, permission_id: str) -> Optional[Permission]:
        """Get permission by ID."""
        return self.session.query(Permission).filter(Permission.id == permission_id).first()

    def get_by_code(self, code: str) -> Optional[Permission]:
        """Get permission by code."""
        return self.session.query(Permission).filter(Permission.code == code).first()

    def list_all(self) -> List[Permission]:
        """List all permissions."""
        return self.session.query(Permission).all()

    def get_by_codes(self, codes: List[str]) -> List[Permission]:
        """Get permissions by codes."""
        return self.session.query(Permission).filter(Permission.code.in_(codes)).all()

    def delete(self, permission_id: str) -> None:
        """Delete a permission."""
        permission = self.get_by_id(permission_id)
        if not permission:
            raise ResourceNotFoundException(f"Permission {permission_id} not found")

        self.session.delete(permission)
        self.session.flush()
