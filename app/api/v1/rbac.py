"""
RBAC API endpoints for roles and permissions.

Handles role CRUD operations and permission management.
"""

from typing import List, Annotated
from fastapi import APIRouter, Depends, status, HTTPException

from app.core.dependencies import get_current_user_with_roles, RequestContext, get_db_session
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.services.role import RoleService
from app.services.permission import PermissionService
from app.schemas.rbac import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    PermissionResponse,
    RolePermissionAssign,
)
from app.models.role import Role
from app.models.permission import Permission
from sqlalchemy.orm import Session

router = APIRouter(tags=["rbac"])


# Role Endpoints


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """List all roles for the current tenant."""
    role_service = RoleService(session)
    roles = role_service.list_roles(str(current_user.tenant_id))
    return [RoleResponse.model_validate(role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Create a new role."""
    try:
        role_service = RoleService(session)
        role = role_service.create_role(
            str(current_user.tenant_id), role_data.name, role_data.description
        )
        return RoleResponse.model_validate(role)
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Get a specific role."""
    try:
        role_service = RoleService(session)
        role = role_service.get_role(role_id, str(current_user.tenant_id))
        return RoleResponse.model_validate(role)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Update a role."""
    try:
        role_service = RoleService(session)
        role = role_service.update_role(
            role_id, str(current_user.tenant_id), name=role_data.name, description=role_data.description
        )
        return RoleResponse.model_validate(role)
    except (ResourceNotFoundException, ValidationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Delete a role."""
    try:
        role_service = RoleService(session)
        role_service.delete_role(role_id, str(current_user.tenant_id))
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Permission Endpoints


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """List all available permissions."""
    permission_service = PermissionService(session)
    permissions = permission_service.list_all_permissions()
    return [PermissionResponse.model_validate(perm) for perm in permissions]


# Role Permission Endpoints


@router.post("/roles/{role_id}/permissions", response_model=RoleResponse, status_code=status.HTTP_200_OK)
async def assign_permissions(
    role_id: str,
    permission_data: RolePermissionAssign,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Assign permissions to a role."""
    try:
        role_service = RoleService(session)
        role = role_service.set_role_permissions(
            role_id, str(current_user.tenant_id), permission_data.permission_ids
        )
        return RoleResponse.model_validate(role)
    except (ResourceNotFoundException, ValidationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_permission(
    role_id: str,
    permission_id: str,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Remove a permission from a role."""
    try:
        role_service = RoleService(session)
        role_service.remove_permission_from_role(role_id, permission_id, str(current_user.tenant_id))
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
