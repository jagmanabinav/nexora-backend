"""
Tests for Phase 4 Application Registry.

Tests application management, API keys, and OAuth providers.
"""

import pytest
from sqlalchemy.orm import Session
import secrets
import hashlib

from backend.app.core.security import generate_id
from backend.app.repositories.application import ApplicationRepository
from backend.app.repositories.api_key import APIKeyRepository
from backend.app.repositories.oauth_provider import OAuthProviderRepository
from backend.app.services.application import ApplicationService
from backend.app.core.exceptions import NotFoundError, ValidationError


@pytest.fixture
def tenant_id() -> str:
    return generate_request_id()


@pytest.fixture
def app_service(db_session: Session) -> ApplicationService:
    return ApplicationService(db_session)


class TestApplicationRepository:
    """Tests for ApplicationRepository."""

    def test_create_application(self, db_session: Session, tenant_id: str):
        """Test creating an application."""
        repo = ApplicationRepository(db_session)
        app = repo.create(tenant_id, "My App", "Test application")

        assert app.name == "My App"
        assert app.tenant_id == tenant_id
        assert app.status == "draft"

    def test_get_application_by_id(self, db_session: Session, tenant_id: str):
        """Test getting application by ID."""
        repo = ApplicationRepository(db_session)
        app = repo.create(tenant_id, "Test App", "Description")

        retrieved = repo.get_by_id(app.id, tenant_id)
        assert retrieved.id == app.id
        assert retrieved.name == "Test App"

    def test_get_application_wrong_tenant(self, db_session: Session, tenant_id: str):
        """Test getting application with wrong tenant returns None."""
        repo = ApplicationRepository(db_session)
        app = repo.create(tenant_id, "App", "Desc")

        wrong_tenant = generate_request_id()
        retrieved = repo.get_by_id(app.id, wrong_tenant)
        assert retrieved is None

    def test_list_applications_by_tenant(self, db_session: Session, tenant_id: str):
        """Test listing applications by tenant."""
        repo = ApplicationRepository(db_session)
        repo.create(tenant_id, "App 1", "First")
        repo.create(tenant_id, "App 2", "Second")

        apps = repo.list_by_tenant(tenant_id)
        assert len(apps) == 2

    def test_update_application(self, db_session: Session, tenant_id: str):
        """Test updating an application."""
        repo = ApplicationRepository(db_session)
        app = repo.create(tenant_id, "Old Name", "Old desc")

        updated = repo.update(app.id, tenant_id, name="New Name", description="New desc")
        assert updated.name == "New Name"
        assert updated.description == "New desc"

    def test_application_lifecycle(self, db_session: Session, tenant_id: str):
        """Test application status changes."""
        repo = ApplicationRepository(db_session)
        app = repo.create(tenant_id, "App", "Test")

        assert app.status == "draft"

        active = repo.set_status(app.id, tenant_id, "active")
        assert active.status == "active"

        suspended = repo.set_status(app.id, tenant_id, "suspended")
        assert suspended.status == "suspended"


class TestAPIKeyRepository:
    """Tests for APIKeyRepository."""

    def test_create_api_key(self, db_session: Session, tenant_id: str):
        """Test creating an API key."""
        app_repo = ApplicationRepository(db_session)
        app = app_repo.create(tenant_id, "App", "Test")

        key_repo = APIKeyRepository(db_session)
        key_hash = hashlib.sha256(b"test_key").hexdigest()
        api_key = key_repo.create(app.id, tenant_id, "Production Key", key_hash)

        assert api_key.name == "Production Key"
        assert api_key.is_revoked == False

    def test_get_api_key_by_hash(self, db_session: Session, tenant_id: str):
        """Test getting API key by hash."""
        app_repo = ApplicationRepository(db_session)
        app = app_repo.create(tenant_id, "App", "Test")

        key_repo = APIKeyRepository(db_session)
        plain = "my_secret_key_12345"
        key_hash = hashlib.sha256(plain.encode()).hexdigest()
        api_key = key_repo.create(app.id, tenant_id, "Key1", key_hash)

        retrieved = key_repo.get_by_hash(key_hash)
        assert retrieved.id == api_key.id

    def test_revoke_api_key(self, db_session: Session, tenant_id: str):
        """Test revoking an API key."""
        app_repo = ApplicationRepository(db_session)
        app = app_repo.create(tenant_id, "App", "Test")

        key_repo = APIKeyRepository(db_session)
        key_hash = hashlib.sha256(b"key").hexdigest()
        api_key = key_repo.create(app.id, tenant_id, "Key", key_hash)

        revoked = key_repo.revoke(api_key.id, tenant_id)
        assert revoked.is_revoked == True

    def test_list_active_api_keys(self, db_session: Session, tenant_id: str):
        """Test listing active API keys."""
        app_repo = ApplicationRepository(db_session)
        app = app_repo.create(tenant_id, "App", "Test")

        key_repo = APIKeyRepository(db_session)
        key1 = key_repo.create(app.id, tenant_id, "Key1", hashlib.sha256(b"k1").hexdigest())
        key2 = key_repo.create(app.id, tenant_id, "Key2", hashlib.sha256(b"k2").hexdigest())

        key_repo.revoke(key1.id, tenant_id)

        active_keys = key_repo.list_active_by_application(app.id, tenant_id)
        assert len(active_keys) == 1
        assert active_keys[0].id == key2.id


class TestOAuthProviderRepository:
    """Tests for OAuthProviderRepository."""

    def test_create_oauth_provider(self, db_session: Session, tenant_id: str):
        """Test creating an OAuth provider."""
        app_repo = ApplicationRepository(db_session)
        app = app_repo.create(tenant_id, "App", "Test")

        oauth_repo = OAuthProviderRepository(db_session)
        provider = oauth_repo.create(
            app.id,
            tenant_id,
            "google",
            "client_id_123",
            "client_secret_456",
        )

        assert provider.provider_name == "google"
        assert provider.client_id == "client_id_123"

    def test_get_oauth_provider_by_name(self, db_session: Session, tenant_id: str):
        """Test getting OAuth provider by name."""
        app_repo = ApplicationRepository(db_session)
        app = app_repo.create(tenant_id, "App", "Test")

        oauth_repo = OAuthProviderRepository(db_session)
        provider = oauth_repo.create(app.id, tenant_id, "github", "github_id", "github_secret")

        retrieved = oauth_repo.get_by_application_and_provider(app.id, tenant_id, "github")
        assert retrieved.id == provider.id

    def test_list_oauth_providers(self, db_session: Session, tenant_id: str):
        """Test listing OAuth providers for an application."""
        app_repo = ApplicationRepository(db_session)
        app = app_repo.create(tenant_id, "App", "Test")

        oauth_repo = OAuthProviderRepository(db_session)
        oauth_repo.create(app.id, tenant_id, "google", "gid", "gsecret")
        oauth_repo.create(app.id, tenant_id, "github", "ghid", "ghsecret")

        providers = oauth_repo.list_by_application(app.id, tenant_id)
        assert len(providers) == 2


class TestApplicationService:
    """Tests for ApplicationService."""

    def test_create_application_service(self, db_session: Session, tenant_id: str, app_service):
        """Test creating an application via service."""
        app = app_service.create_application(tenant_id, "App", "Description")

        assert app.name == "App"
        assert app.status == "draft"

    def test_create_duplicate_application_name(self, db_session: Session, tenant_id: str, app_service):
        """Test that duplicate application names are rejected."""
        app_service.create_application(tenant_id, "App", "First")

        with pytest.raises(ValidationError):
            app_service.create_application(tenant_id, "App", "Second")

    def test_activate_application(self, db_session: Session, tenant_id: str, app_service):
        """Test activating an application."""
        app = app_service.create_application(tenant_id, "App", "Test")
        assert app.status == "draft"

        active = app_service.activate_application(app.id, tenant_id)
        assert active.status == "active"

    def test_suspend_application(self, db_session: Session, tenant_id: str, app_service):
        """Test suspending an application."""
        app = app_service.create_application(tenant_id, "App", "Test")
        app = app_service.activate_application(app.id, tenant_id)

        suspended = app_service.suspend_application(app.id, tenant_id)
        assert suspended.status == "suspended"

    def test_generate_api_key(self, db_session: Session, tenant_id: str, app_service):
        """Test generating an API key."""
        app = app_service.create_application(tenant_id, "App", "Test")

        plain_key, api_key = app_service.generate_api_key(app.id, tenant_id, "Production")

        assert api_key.name == "Production"
        assert len(plain_key) > 20  # Should be a long random string
        assert api_key.is_revoked == False

    def test_revoke_api_key(self, db_session: Session, tenant_id: str, app_service):
        """Test revoking an API key."""
        app = app_service.create_application(tenant_id, "App", "Test")
        plain_key, api_key = app_service.generate_api_key(app.id, tenant_id, "Key")

        revoked = app_service.revoke_api_key(api_key.id, tenant_id)
        assert revoked.is_revoked == True

    def test_list_api_keys(self, db_session: Session, tenant_id: str, app_service):
        """Test listing API keys for an application."""
        app = app_service.create_application(tenant_id, "App", "Test")

        _, key1 = app_service.generate_api_key(app.id, tenant_id, "Key1")
        _, key2 = app_service.generate_api_key(app.id, tenant_id, "Key2")

        keys = app_service.list_api_keys(app.id, tenant_id)
        assert len(keys) == 2

    def test_add_oauth_provider(self, db_session: Session, tenant_id: str, app_service):
        """Test adding an OAuth provider."""
        app = app_service.create_application(tenant_id, "App", "Test")

        provider = app_service.add_oauth_provider(
            app.id, tenant_id, "google", "client_id", "client_secret"
        )

        assert provider.provider_name == "google"
        assert provider.client_id == "client_id"

    def test_add_duplicate_oauth_provider(self, db_session: Session, tenant_id: str, app_service):
        """Test that duplicate OAuth providers are rejected."""
        app = app_service.create_application(tenant_id, "App", "Test")

        app_service.add_oauth_provider(app.id, tenant_id, "google", "id1", "secret1")

        with pytest.raises(ValidationError):
            app_service.add_oauth_provider(app.id, tenant_id, "google", "id2", "secret2")

    def test_list_oauth_providers(self, db_session: Session, tenant_id: str, app_service):
        """Test listing OAuth providers."""
        app = app_service.create_application(tenant_id, "App", "Test")

        app_service.add_oauth_provider(app.id, tenant_id, "google", "gid", "gsecret")
        app_service.add_oauth_provider(app.id, tenant_id, "github", "ghid", "ghsecret")

        providers = app_service.list_oauth_providers(app.id, tenant_id)
        assert len(providers) == 2

    def test_tenant_isolation(self, db_session: Session, app_service):
        """Test that applications are isolated by tenant."""
        tenant_1 = generate_request_id()
        tenant_2 = generate_request_id()

        app_service.create_application(tenant_1, "App1", "Tenant 1 app")
        app_service.create_application(tenant_2, "App2", "Tenant 2 app")

        apps_tenant_1 = app_service.list_applications(tenant_1)
        apps_tenant_2 = app_service.list_applications(tenant_2)

        assert len(apps_tenant_1) == 1
        assert len(apps_tenant_2) == 1
        assert apps_tenant_1[0].name == "App1"
        assert apps_tenant_2[0].name == "App2"
