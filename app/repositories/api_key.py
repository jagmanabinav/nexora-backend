"""
API Key repository for data access.

Provides tenant-scoped API key management.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.api_key import APIKey
from app.core.exceptions import ResourceNotFoundException
from uuid import uuid4


class APIKeyRepository:
    """Repository for API key data access with tenant scoping."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, application_id: str, tenant_id: str, name: str, key_hash: str) -> APIKey:
        """Create a new API key."""
        key_id = uuid4()
        api_key = APIKey(
            id=key_id,
            application_id=application_id,
            tenant_id=tenant_id,
            name=name,
            key_hash=key_hash,
            is_revoked=False,
        )
        self.session.add(api_key)
        self.session.flush()
        return api_key

    def get_by_id(self, key_id: str, tenant_id: str) -> Optional[APIKey]:
        """Get API key by ID, scoped to tenant."""
        return self.session.query(APIKey).filter(
            and_(APIKey.id == key_id, APIKey.tenant_id == tenant_id)
        ).first()

    def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash."""
        return self.session.query(APIKey).filter(APIKey.key_hash == key_hash).first()

    def list_by_application(self, application_id: str, tenant_id: str) -> List[APIKey]:
        """List all API keys for an application."""
        return self.session.query(APIKey).filter(
            and_(
                APIKey.application_id == application_id,
                APIKey.tenant_id == tenant_id,
            )
        ).all()

    def list_active_by_application(self, application_id: str, tenant_id: str) -> List[APIKey]:
        """List all active (not revoked) API keys for an application."""
        return self.session.query(APIKey).filter(
            and_(
                APIKey.application_id == application_id,
                APIKey.tenant_id == tenant_id,
                APIKey.is_revoked == False,
            )
        ).all()

    def revoke(self, key_id: str, tenant_id: str) -> APIKey:
        """Revoke an API key."""
        api_key = self.get_by_id(key_id, tenant_id)
        if not api_key:
            raise ResourceNotFoundException(f"API key {key_id} not found")

        api_key.is_revoked = True
        self.session.flush()
        return api_key

    def delete(self, key_id: str, tenant_id: str) -> None:
        """Delete an API key."""
        api_key = self.get_by_id(key_id, tenant_id)
        if not api_key:
            raise ResourceNotFoundException(f"API key {key_id} not found")

        self.session.delete(api_key)
        self.session.flush()
