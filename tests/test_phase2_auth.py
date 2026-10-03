"""Authentication tests for Phase 2."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


# ============================================================================
# Registration Tests
# ============================================================================

def test_register_success(client):
    """Test successful user registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123",
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "Test Organization",
            "tenant_slug": "test-org",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "user" in data["data"]
    assert "tenant" in data["data"]
    assert "tokens" in data["data"]
    assert "access_token" in data["data"]["tokens"]
    assert "refresh_token" in data["data"]["tokens"]


def test_register_duplicate_email(client):
    """Test registration with duplicate email."""
    # First registration
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "TestPassword123",
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "First Org",
            "tenant_slug": "first-org",
        }
    )

    # Second registration with same email
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "TestPassword456",
            "first_name": "Jane",
            "last_name": "Smith",
            "tenant_name": "Second Org",
            "tenant_slug": "second-org",
        }
    )

    assert response.status_code == 409


def test_register_duplicate_tenant_slug(client):
    """Test registration with duplicate tenant slug."""
    # First registration
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "user1@example.com",
            "password": "TestPassword123",
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "First Org",
            "tenant_slug": "duplicate-slug",
        }
    )

    # Second registration with same slug
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user2@example.com",
            "password": "TestPassword456",
            "first_name": "Jane",
            "last_name": "Smith",
            "tenant_name": "Second Org",
            "tenant_slug": "duplicate-slug",
        }
    )

    assert response.status_code == 409


def test_register_weak_password(client):
    """Test registration with weak password."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "weak",  # Too short and no uppercase/digits
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "Test Org",
            "tenant_slug": "test-org",
        }
    )

    assert response.status_code == 422


def test_register_missing_uppercase_password(client):
    """Test registration with password missing uppercase."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",  # No uppercase
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "Test Org",
            "tenant_slug": "test-org",
        }
    )

    assert response.status_code == 422


# ============================================================================
# Login Tests
# ============================================================================

def test_login_success(client):
    """Test successful login."""
    # Register first
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "TestPassword123",
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "Login Org",
            "tenant_slug": "login-org",
        }
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "TestPassword123",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "tokens" in data["data"]


def test_login_invalid_email(client):
    """Test login with invalid email."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "TestPassword123",
        }
    )

    assert response.status_code == 401


def test_login_wrong_password(client):
    """Test login with wrong password."""
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "TestPassword123",
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "Wrong Pass Org",
            "tenant_slug": "wrong-pass-org",
        }
    )

    # Login with wrong password
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPassword456",
        }
    )

    assert response.status_code == 401


# ============================================================================
# Token Management Tests
# ============================================================================

def test_refresh_token_success(client):
    """Test successful token refresh."""
    # Register and get tokens
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "TestPassword123",
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "Refresh Org",
            "tenant_slug": "refresh-org",
        }
    )

    refresh_token = register_response.json()["data"]["tokens"]["refresh_token"]

    # Refresh
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "tokens" in data["data"]
    assert "access_token" in data["data"]["tokens"]


def test_refresh_token_invalid(client):
    """Test refresh with invalid token."""
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"}
    )

    assert response.status_code == 401


def test_logout_success(client):
    """Test successful logout."""
    # Register and get tokens
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "TestPassword123",
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "Logout Org",
            "tenant_slug": "logout-org",
        }
    )

    access_token = register_response.json()["data"]["tokens"]["access_token"]

    # Logout
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_logout_invalid_token(client):
    """Test logout with invalid token."""
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer invalid.token"}
    )

    assert response.status_code == 401


# ============================================================================
# Current User Tests
# ============================================================================

def test_get_current_user_success(client):
    """Test getting current user info."""
    # Register and get tokens
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "TestPassword123",
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "Me Org",
            "tenant_slug": "me-org",
        }
    )

    access_token = register_response.json()["data"]["tokens"]["access_token"]

    # Get current user
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "user" in data["data"]
    assert "tenant" in data["data"]
    assert data["data"]["user"]["email"] == "me@example.com"


def test_get_current_user_no_auth(client):
    """Test getting current user without auth."""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


# ============================================================================
# Tenant Isolation Tests
# ============================================================================

def test_tenant_isolation_on_login(client):
    """Test that users from different tenants are isolated."""
    # Register first tenant/user
    response1 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user1@example.com",
            "password": "TestPassword123",
            "first_name": "User",
            "last_name": "One",
            "tenant_name": "Tenant One",
            "tenant_slug": "tenant-one",
        }
    )

    # Register second tenant/user
    response2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user2@example.com",
            "password": "TestPassword456",
            "first_name": "User",
            "last_name": "Two",
            "tenant_name": "Tenant Two",
            "tenant_slug": "tenant-two",
        }
    )

    tenant_id_1 = response1.json()["data"]["tenant"]["id"]
    tenant_id_2 = response2.json()["data"]["tenant"]["id"]

    # Tenants should be different
    assert tenant_id_1 != tenant_id_2


def test_tenant_isolation_token_payload(client):
    """Test that JWT token contains tenant_id."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "token@example.com",
            "password": "TestPassword123",
            "first_name": "John",
            "last_name": "Doe",
            "tenant_name": "Token Org",
            "tenant_slug": "token-org",
        }
    )

    access_token = response.json()["data"]["tokens"]["access_token"]
    tenant_id = response.json()["data"]["tenant"]["id"]

    # Decode token (without verification for test purposes)
    import base64
    import json
    parts = access_token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))

    assert "tenant_id" in payload
    assert payload["tenant_id"] == tenant_id
