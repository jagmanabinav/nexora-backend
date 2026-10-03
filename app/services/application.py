"""
Application service for business logic.

Manages application lifecycle and operations.
"""

from typing import List, Optional
import secrets
import hashlib
from sqlalchemy.orm import Session

from app.repositories.application import ApplicationRepository
from app.repositories.api_key import APIKeyRepository
from app.repositories.oauth_provider import OAuthProviderRepository
from app.models.application import Application
from app.models.api_key import APIKey
from app.core.exceptions import ResourceNotFoundException, ValidationException


class ApplicationService:
    """Service for application management."""

    def __init__(self, session: Session):
        self.session = session
        self.app_repo = ApplicationRepository(session)
        self.api_key_repo = APIKeyRepository(session)
        self.oauth_repo = OAuthProviderRepository(session)

    def create_application(
        self,
        tenant_id: str,
        name: str,
        description: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> Application:
        """Create a new application."""
        # Check for duplicate name
        existing = self.app_repo.get_by_name(tenant_id, name)
        if existing:
            raise ValidationException(f"Application '{name}' already exists in this tenant")

        application = self.app_repo.create(tenant_id, name, description, webhook_url)
        self.session.commit()
        return application

    def list_applications(self, tenant_id: str, status: Optional[str] = None) -> List[Application]:
        """List all applications for a tenant."""
        return self.app_repo.list_by_tenant(tenant_id, status)

    def get_application(self, app_id: str, tenant_id: str) -> Application:
        """Get a single application."""
        application = self.app_repo.get_by_id(app_id, tenant_id)
        if not application:
            raise ResourceNotFoundException("Application not found")
        return application

    def update_application(
        self,
        app_id: str,
        tenant_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> Application:
        """Update application details."""
        application = self.app_repo.get_by_id(app_id, tenant_id)
        if not application:
            raise ResourceNotFoundException("Application not found")

        # Check for duplicate name if changing
        if name and name != application.name:
            existing = self.app_repo.get_by_name(tenant_id, name)
            if existing:
                raise ValidationException(f"Application '{name}' already exists in this tenant")

        application = self.app_repo.update(
            app_id, tenant_id, name=name, description=description, webhook_url=webhook_url
        )
        self.session.commit()
        return application

    def delete_application(self, app_id: str, tenant_id: str) -> None:
        """Delete an application."""
        self.app_repo.delete(app_id, tenant_id)
        self.session.commit()

    def activate_application(self, app_id: str, tenant_id: str) -> Application:
        """Activate a draft application."""
        application = self.app_repo.get_by_id(app_id, tenant_id)
        if not application:
            raise ResourceNotFoundException("Application not found")

        if application.status == "archived":
            raise ValidationException("Cannot activate archived application")

        application = self.app_repo.set_status(app_id, tenant_id, "active")
        self.session.commit()
        return application

    def suspend_application(self, app_id: str, tenant_id: str) -> Application:
        """Suspend an active application."""
        application = self.app_repo.get_by_id(app_id, tenant_id)
        if not application:
            raise ResourceNotFoundException("Application not found")

        application = self.app_repo.set_status(app_id, tenant_id, "suspended")
        self.session.commit()
        return application

    def generate_api_key(self, app_id: str, tenant_id: str, name: str) -> tuple[str, APIKey]:
        """Generate a new API key for an application.
        
        Returns (plain_key, api_key_object).
        Plain key should be shown to user only once.
        """
        application = self.app_repo.get_by_id(app_id, tenant_id)
        if not application:
            raise ResourceNotFoundException("Application not found")

        # Generate random key
        plain_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()

        api_key = self.api_key_repo.create(app_id, tenant_id, name, key_hash)
        self.session.commit()

        return plain_key, api_key

    def revoke_api_key(self, key_id: str, tenant_id: str) -> APIKey:
        """Revoke an API key."""
        api_key = self.api_key_repo.revoke(key_id, tenant_id)
        self.session.commit()
        return api_key

    def list_api_keys(self, app_id: str, tenant_id: str) -> List[APIKey]:
        """List all API keys for an application."""
        application = self.app_repo.get_by_id(app_id, tenant_id)
        if not application:
            raise ResourceNotFoundException("Application not found")

        return self.api_key_repo.list_by_application(app_id, tenant_id)

    def add_oauth_provider(
        self,
        app_id: str,
        tenant_id: str,
        provider_name: str,
        client_id: str,
        client_secret: str,
        redirect_url: Optional[str] = None,
        scopes: Optional[str] = None,
    ):
        """Add an OAuth provider to an application."""
        application = self.app_repo.get_by_id(app_id, tenant_id)
        if not application:
            raise ResourceNotFoundException("Application not found")

        # Check if already exists
        existing = self.oauth_repo.get_by_application_and_provider(
            app_id, tenant_id, provider_name
        )
        if existing:
            raise ValidationException(f"OAuth provider '{provider_name}' already configured")

        provider = self.oauth_repo.create(
            app_id, tenant_id, provider_name, client_id, client_secret, redirect_url, scopes
        )
        self.session.commit()
        return provider

    def list_oauth_providers(self, app_id: str, tenant_id: str):
        """List all OAuth providers for an application."""
        application = self.app_repo.get_by_id(app_id, tenant_id)
        if not application:
            raise ResourceNotFoundException("Application not found")

        return self.oauth_repo.list_by_application(app_id, tenant_id)
