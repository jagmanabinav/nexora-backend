"""
Schemas for application registry operations.

Validates request/response data for application endpoints.
"""

from typing import List, Optional, Annotated
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, StringConstraints, HttpUrl


class ApplicationCreate(BaseModel):
    """Schema for creating an application."""

    name: Annotated[str, StringConstraints(min_length=1, max_length=255)] = Field(..., description="Application name")
    description: Optional[str] = Field(None, description="Application description")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for events")


class ApplicationUpdate(BaseModel):
    """Schema for updating an application."""

    name: Optional[Annotated[str, StringConstraints(min_length=1, max_length=255)]] = Field(
        None, description="Application name"
    )
    description: Optional[str] = Field(None, description="Application description")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for events")


class ApplicationResponse(BaseModel):
    """Application response schema."""

    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str] = None
    status: str  # draft, active, suspended, archived
    webhook_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""

    name: Annotated[str, StringConstraints(min_length=1, max_length=255)] = Field(
        ..., description="API key name"
    )


class APIKeyResponse(BaseModel):
    """API key response schema (without secret)."""

    id: UUID
    name: str
    created_at: datetime
    is_revoked: bool

    class Config:
        from_attributes = True


class APIKeySecret(BaseModel):
    """API key response with secret (shown only once)."""

    id: UUID
    name: str
    key: str  # Plain key (only shown once)
    created_at: datetime

    class Config:
        from_attributes = True


class OAuthProviderCreate(BaseModel):
    """Schema for creating an OAuth provider."""

    provider_name: Annotated[str, StringConstraints(min_length=1, max_length=100)] = Field(
        ..., description="OAuth provider name (google, github, etc.)"
    )
    client_id: Annotated[str, StringConstraints(min_length=1, max_length=255)] = Field(
        ..., description="OAuth client ID"
    )
    client_secret: Annotated[str, StringConstraints(min_length=1, max_length=255)] = Field(
        ..., description="OAuth client secret"
    )
    redirect_url: Optional[str] = Field(None, description="Redirect URL")
    scopes: Optional[str] = Field(None, description="Comma-separated scopes")


class OAuthProviderResponse(BaseModel):
    """OAuth provider response schema."""

    id: UUID
    provider_name: str
    redirect_url: Optional[str] = None
    scopes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
