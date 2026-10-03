"""
UserRole repository for data access.

Provides tenant-scoped user role management.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user_role import UserRole
from app.core.exceptions import ResourceNotFoundException
from uuid import uuid4


class UserRoleRepository:
    """Repository for user role assignment with tenant scoping."""

    def __init__(self, session: Session):
        self.session = session

    def assign(self, user_id: str, role_id: str, tenant_id: str) -> UserRole:
        """Assign a role to a user within a tenant."""
        # Check if already assigned
        existing = self.session.query(UserRole).filter(
            and_(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
                UserRole.tenant_id == tenant_id,
            )
        ).first()

        if existing:
            return existing

        user_role_id = uuid4()
        user_role = UserRole(
            id=user_role_id,
            user_id=user_id,
            role_id=role_id,
            tenant_id=tenant_id,
        )
        self.session.add(user_role)
        self.session.flush()
        return user_role

    def unassign(self, user_id: str, role_id: str, tenant_id: str) -> None:
        """Remove a role from a user."""
        user_role = self.session.query(UserRole).filter(
            and_(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
                UserRole.tenant_id == tenant_id,
            )
        ).first()

        if user_role:
            self.session.delete(user_role)
            self.session.flush()

    def get_user_roles(self, user_id: str, tenant_id: str) -> List[UserRole]:
        """Get all roles assigned to a user in a tenant."""
        return self.session.query(UserRole).filter(
            and_(UserRole.user_id == user_id, UserRole.tenant_id == tenant_id)
        ).all()

    def get_role_users(self, role_id: str, tenant_id: str) -> List[UserRole]:
        """Get all users assigned to a role in a tenant."""
        return self.session.query(UserRole).filter(
            and_(UserRole.role_id == role_id, UserRole.tenant_id == tenant_id)
        ).all()

    def has_role(self, user_id: str, role_id: str, tenant_id: str) -> bool:
        """Check if user has a specific role in tenant."""
        return (
            self.session.query(UserRole)
            .filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id,
                    UserRole.tenant_id == tenant_id,
                )
            )
            .first()
            is not None
        )

    def delete_user_roles(self, user_id: str, tenant_id: str) -> None:
        """Delete all roles for a user in a tenant."""
        self.session.query(UserRole).filter(
            and_(UserRole.user_id == user_id, UserRole.tenant_id == tenant_id)
        ).delete()
        self.session.flush()
