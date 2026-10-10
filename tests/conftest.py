"""Shared fixtures for isolated API tests."""

from collections.abc import Generator
import os
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.engine import Connection
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# The test process must not depend on a developer's ignored .env file.
os.environ.setdefault("JWT_SECRET", "pytest-only-signing-secret-change-me-123456")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())

import app.main  # noqa: E402
from app.core.dependencies import get_db, get_db_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base  # noqa: E402


@compiles(PostgreSQLUUID, "sqlite")
def compile_postgresql_uuid_for_sqlite(_type, _compiler, **_kwargs):
    return "CHAR(36)"


_postgresql_uuid_bind_processor = PostgreSQLUUID.bind_processor


def _bind_postgresql_uuid_for_sqlite(type_, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            return (value if isinstance(value, UUID) else UUID(str(value))).hex

        return process
    return _postgresql_uuid_bind_processor(type_, dialect)


PostgreSQLUUID.bind_processor = _bind_postgresql_uuid_for_sqlite


@compiles(JSONB, "sqlite")
def compile_postgresql_jsonb_for_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture(scope="session")
def test_engine():
    """Create an in-memory database with the production model metadata."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """Provide a session whose transaction is rolled back after each test."""
    connection: Connection = test_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a test client whose database dependencies use the isolated session."""

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_session] = override_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client: TestClient):
    """Register a fresh user and return the client, account data, and tokens."""
    import secrets

    suffix = secrets.token_hex(6)
    account = {
        "email": f"pytest-{suffix}@example.com",
        "password": "LocalTest!2345",
        "first_name": "Pytest",
        "last_name": "User",
        "tenant_name": f"Pytest Tenant {suffix}",
        "tenant_slug": f"pytest-{suffix}",
    }
    response = client.post("/api/v1/auth/register", json=account)
    assert response.status_code == 200, response.text

    result = response.json()["data"]
    tokens = result["tokens"]
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return {
        "client": client,
        "account": account,
        "user": result["user"],
        "tenant": result["tenant"],
        "tokens": tokens,
    }
