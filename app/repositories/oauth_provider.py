"""
OAuth Provider repository for data access.

Provides tenant-scoped OAuth provider management.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.oauth_provider import OAuthProvider
from app.core.exceptions import ResourceNotFoundException
from uuid import uuid4


class OAuthProviderRepository:
    """Repository for OAuth provider data access with tenant scoping."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        application_id: str,
        tenant_id: str,
        provider_name: str,
        client_id: str,
        client_secret: str,
        redirect_url: Optional[str] = None,
        scopes: Optional[str] = None,
    ) -> OAuthProvider:
        """Create a new OAuth provider."""
        provider_id = uuid4()
        provider = OAuthProvider(
            id=provider_id,
            application_id=application_id,
            tenant_id=tenant_id,
            provider_name=provider_name,
            client_id=client_id,
            client_secret=client_secret,
            redirect_url=redirect_url,
            scopes=scopes,
        )
        self.session.add(provider)
        self.session.flush()
        return provider

    def get_by_id(self, provider_id: str, tenant_id: str) -> Optional[OAuthProvider]:
        """Get OAuth provider by ID, scoped to tenant."""
        return self.session.query(OAuthProvider).filter(
            and_(OAuthProvider.id == provider_id, OAuthProvider.tenant_id == tenant_id)
        ).first()

    def get_by_application_and_provider(
        self, application_id: str, tenant_id: str, provider_name: str
    ) -> Optional[OAuthProvider]:
        """Get OAuth provider by application and provider name."""
        return self.session.query(OAuthProvider).filter(
            and_(
                OAuthProvider.application_id == application_id,
                OAuthProvider.tenant_id == tenant_id,
                OAuthProvider.provider_name == provider_name,
            )
        ).first()

    def list_by_application(self, application_id: str, tenant_id: str) -> List[OAuthProvider]:
        """List all OAuth providers for an application."""
        return self.session.query(OAuthProvider).filter(
            and_(
                OAuthProvider.application_id == application_id,
                OAuthProvider.tenant_id == tenant_id,
            )
        ).all()

    def update(self, provider_id: str, tenant_id: str, **kwargs) -> OAuthProvider:
        """Update OAuth provider fields."""
        provider = self.get_by_id(provider_id, tenant_id)
        if not provider:
            raise ResourceNotFoundException(f"OAuth provider {provider_id} not found")

        for key, value in kwargs.items():
            if hasattr(provider, key) and value is not None:
                setattr(provider, key, value)

        self.session.flush()
        return provider

    def delete(self, provider_id: str, tenant_id: str) -> None:
        """Delete an OAuth provider."""
        provider = self.get_by_id(provider_id, tenant_id)
        if not provider:
            raise ResourceNotFoundException(f"OAuth provider {provider_id} not found")

        self.session.delete(provider)
        self.session.flush()
