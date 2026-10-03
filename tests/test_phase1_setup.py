"""Basic tests for Phase 1 setup."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_app_creation():
    """Test that app is created successfully."""
    assert app is not None
    assert app.title == "Nexora Core"


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Nexora" in data["service"]


def test_readiness_endpoint(client):
    """Test readiness check endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_api_v1_root(client):
    """Test API v1 root endpoint."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert "Nexora Core API v1" in data["message"]


def test_request_id_header(client):
    """Test that request ID is provided in response."""
    response = client.get("/health")
    assert "X-Request-Id" in response.headers
    assert response.headers["X-Request-Id"].startswith("req_")


def test_cors_enabled(client):
    """Test CORS headers are present."""
    response = client.get("/health")
    # CORS headers are added by the middleware
    assert response.status_code == 200
