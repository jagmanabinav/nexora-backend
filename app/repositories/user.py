"""User repository for data access."""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Repository for user data access."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str, tenant_id: Optional[UUID] = None) -> Optional[User]:
        """Get user by email, optionally filtered by tenant."""
        query = self.db.query(User).filter(User.email == email)
        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)
        return query.first()

    def get_by_tenant(self, tenant_id: UUID, user_id: UUID) -> Optional[User]:
        """Get user by tenant and user ID (enforces tenant isolation)."""
        return self.db.query(User).filter(
            User.id == user_id,
            User.tenant_id == tenant_id
        ).first()

    def create(
        self,
        tenant_id: UUID,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None
    ) -> User:
        """Create a new user."""
        user = User(
            tenant_id=tenant_id,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        self.db.add(user)
        self.db.flush()
        return user

    def update(self, user_id: UUID, **kwargs) -> Optional[User]:
        """Update user."""
        user = self.get_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        self.db.flush()
        return user

    def delete(self, user_id: UUID) -> bool:
        """Delete user."""
        user = self.get_by_id(user_id)
        if not user:
            return False
        self.db.delete(user)
        return True

    def list_by_tenant(self, tenant_id: UUID, skip: int = 0, limit: int = 100) -> list[User]:
        """List users by tenant."""
        return self.db.query(User).filter(
            User.tenant_id == tenant_id
        ).offset(skip).limit(limit).all()

    def count_by_tenant(self, tenant_id: UUID) -> int:
        """Count users in tenant."""
        return self.db.query(User).filter(User.tenant_id == tenant_id).count()
