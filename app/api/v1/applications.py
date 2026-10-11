"""
Application registry API endpoints.

Handles application CRUD, API key management, and OAuth provider setup.
"""

from typing import List, Annotated
from fastapi import APIRouter, Depends, status, HTTPException

from app.core.dependencies import get_current_user_with_roles, RequestContext, get_db_session
from app.core.authorization import require_permission
from app.core.permissions import PermissionCode
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.services.application import ApplicationService
from app.schemas.applications import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    APIKeyCreate,
    APIKeyResponse,
    APIKeySecret,
    OAuthProviderCreate,
    OAuthProviderResponse,
)
from sqlalchemy.orm import Session

router = APIRouter(tags=["applications"])


# Application Endpoints


@router.get("/applications", response_model=List[ApplicationResponse])
@require_permission(PermissionCode.APPLICATION_LIST)
async def list_applications(
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """List all applications for the current tenant."""
    app_service = ApplicationService(session)
    applications = app_service.list_applications(str(current_user.tenant_id))
    return [ApplicationResponse.model_validate(app) for app in applications]


@router.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
@require_permission(PermissionCode.APPLICATION_CREATE)
async def create_application(
    app_data: ApplicationCreate,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Create a new application."""
    try:
        app_service = ApplicationService(session)
        application = app_service.create_application(
            str(current_user.tenant_id),
            app_data.name,
            app_data.description,
            app_data.webhook_url,
        )
        return ApplicationResponse.model_validate(application)
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/applications/{app_id}", response_model=ApplicationResponse)
@require_permission(PermissionCode.APPLICATION_READ)
async def get_application(
    app_id: str,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Get a specific application."""
    try:
        app_service = ApplicationService(session)
        application = app_service.get_application(app_id, str(current_user.tenant_id))
        return ApplicationResponse.model_validate(application)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/applications/{app_id}", response_model=ApplicationResponse)
@require_permission(PermissionCode.APPLICATION_UPDATE)
async def update_application(
    app_id: str,
    app_data: ApplicationUpdate,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Update an application."""
    try:
        app_service = ApplicationService(session)
        application = app_service.update_application(
            app_id,
            str(current_user.tenant_id),
            name=app_data.name,
            description=app_data.description,
            webhook_url=app_data.webhook_url,
        )
        return ApplicationResponse.model_validate(application)
    except (ResourceNotFoundException, ValidationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/applications/{app_id}/activate", response_model=ApplicationResponse)
@require_permission(PermissionCode.APPLICATION_UPDATE)
async def activate_application(
    app_id: str,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Activate an application."""
    try:
        app_service = ApplicationService(session)
        application = app_service.activate_application(app_id, str(current_user.tenant_id))
        return ApplicationResponse.model_validate(application)
    except (ResourceNotFoundException, ValidationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/applications/{app_id}/suspend", response_model=ApplicationResponse)
@require_permission(PermissionCode.APPLICATION_UPDATE)
async def suspend_application(
    app_id: str,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Suspend an application."""
    try:
        app_service = ApplicationService(session)
        application = app_service.suspend_application(app_id, str(current_user.tenant_id))
        return ApplicationResponse.model_validate(application)
    except (ResourceNotFoundException, ValidationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# API Key Endpoints


@router.get("/applications/{app_id}/api-keys", response_model=List[APIKeyResponse])
@require_permission(PermissionCode.APPLICATION_READ)
async def list_api_keys(
    app_id: str,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """List all API keys for an application."""
    try:
        app_service = ApplicationService(session)
        api_keys = app_service.list_api_keys(app_id, str(current_user.tenant_id))
        return [APIKeyResponse.model_validate(key) for key in api_keys]
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/applications/{app_id}/api-keys", response_model=APIKeySecret, status_code=status.HTTP_201_CREATED)
@require_permission(PermissionCode.APPLICATION_UPDATE)
async def create_api_key(
    app_id: str,
    key_data: APIKeyCreate,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Generate a new API key for an application."""
    try:
        app_service = ApplicationService(session)
        plain_key, api_key = app_service.generate_api_key(
            app_id, str(current_user.tenant_id), key_data.name
        )
        return APIKeySecret(id=api_key.id, name=api_key.name, key=plain_key, created_at=api_key.created_at)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission(PermissionCode.APPLICATION_UPDATE)
async def revoke_api_key(
    key_id: str,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Revoke an API key."""
    try:
        app_service = ApplicationService(session)
        app_service.revoke_api_key(key_id, str(current_user.tenant_id))
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# OAuth Provider Endpoints


@router.get("/applications/{app_id}/oauth-providers", response_model=List[OAuthProviderResponse])
@require_permission(PermissionCode.APPLICATION_READ)
async def list_oauth_providers(
    app_id: str,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """List all OAuth providers for an application."""
    try:
        app_service = ApplicationService(session)
        providers = app_service.list_oauth_providers(app_id, str(current_user.tenant_id))
        return [OAuthProviderResponse.model_validate(p) for p in providers]
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/applications/{app_id}/oauth-providers", response_model=OAuthProviderResponse, status_code=status.HTTP_201_CREATED)
@require_permission(PermissionCode.APPLICATION_UPDATE)
async def create_oauth_provider(
    app_id: str,
    provider_data: OAuthProviderCreate,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Add an OAuth provider to an application."""
    try:
        app_service = ApplicationService(session)
        provider = app_service.add_oauth_provider(
            app_id,
            str(current_user.tenant_id),
            provider_data.provider_name,
            provider_data.client_id,
            provider_data.client_secret,
            provider_data.redirect_url,
            provider_data.scopes,
        )
        return OAuthProviderResponse.model_validate(provider)
    except (ResourceNotFoundException, ValidationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
