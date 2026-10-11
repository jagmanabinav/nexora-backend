"""
RBAC API endpoints for roles and permissions.

Handles role CRUD operations and permission management.
"""

from typing import List, Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException

from app.core.dependencies import get_current_user_with_roles, RequestContext, get_db_session
from app.core.authorization import require_permission
from app.core.permissions import PermissionCode
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.services.role import RoleService
from app.services.permission import PermissionService
from app.schemas.rbac import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    PermissionResponse,
    RolePermissionAssign,
    UserRoleAssign,
    UserRoleResponse,
)
from app.repositories.user import UserRepository
from app.repositories.user_role import UserRoleRepository
from app.repositories.role import RoleRepository
from app.models.role import Role
from app.models.permission import Permission
from app.models.tenant import Tenant
from sqlalchemy.orm import Session

router = APIRouter(tags=["rbac"])


# Role Endpoints


@router.get("/roles", response_model=List[RoleResponse])
@require_permission(PermissionCode.ROLE_LIST)
async def list_roles(
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """List all roles for the current tenant."""
    role_service = RoleService(session)
    roles = role_service.list_roles(str(current_user.tenant_id))
    return [RoleResponse.model_validate(role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
@require_permission(PermissionCode.ROLE_CREATE)
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
@require_permission(PermissionCode.ROLE_READ)
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
@require_permission(PermissionCode.ROLE_UPDATE)
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
@require_permission(PermissionCode.ROLE_DELETE)
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
@require_permission(PermissionCode.PERMISSION_LIST)
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
@require_permission(PermissionCode.ROLE_ASSIGN)
async def assign_permissions(
    role_id: str,
    permission_data: RolePermissionAssign,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Assign permissions to a role."""
    try:
        requested_permissions = (
            session.query(Permission)
            .filter(Permission.id.in_(permission_data.permission_ids))
            .all()
        )
        if (
            any(permission.code.startswith("admin:") for permission in requested_permissions)
            and (
                not current_user.has_role("Super Admin")
                or not session.query(Tenant)
                .filter(
                    Tenant.id == current_user.tenant_id,
                    Tenant.slug == "nexora-platform",
                )
                .first()
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a Super Admin may assign platform permissions",
            )
        role_service = RoleService(session)
        role = role_service.set_role_permissions(
            role_id, str(current_user.tenant_id), permission_data.permission_ids
        )
        return RoleResponse.model_validate(role)
    except HTTPException:
        raise
    except (ResourceNotFoundException, ValidationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission(PermissionCode.ROLE_ASSIGN)
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


@router.post(
    "/users/{user_id}/roles",
    response_model=UserRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
@require_permission(PermissionCode.ROLE_ASSIGN)
async def assign_user_role(
    user_id: UUID,
    role_data: UserRoleAssign,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Assign a role within the authenticated user's tenant."""
    tenant_id = str(current_user.tenant_id)
    user = UserRepository(session).get_by_tenant(current_user.tenant_id, user_id)
    role = RoleRepository(session).get_by_id(str(role_data.role_id), tenant_id)
    if user is None or role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or role not found")

    user_role = UserRoleRepository(session).assign(
        str(user_id), str(role_data.role_id), tenant_id
    )
    session.commit()
    return UserRoleResponse(
        id=user_role.id,
        user_id=user_role.user_id,
        role_id=user_role.role_id,
        role_name=role.name,
        tenant_id=user_role.tenant_id,
        created_at=user_role.created_at,
    )


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@require_permission(PermissionCode.ROLE_ASSIGN)
async def revoke_user_role(
    user_id: UUID,
    role_id: UUID,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """Revoke a role assignment within the authenticated user's tenant."""
    tenant_id = str(current_user.tenant_id)
    user = UserRepository(session).get_by_tenant(current_user.tenant_id, user_id)
    role = RoleRepository(session).get_by_id(str(role_id), tenant_id)
    if user is None or role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or role not found")

    UserRoleRepository(session).unassign(str(user_id), str(role_id), tenant_id)
    session.commit()


@router.get("/users/{user_id}/permissions", response_model=List[PermissionResponse])
@require_permission(PermissionCode.USER_READ)
async def get_user_permissions(
    user_id: UUID,
    current_user: Annotated[RequestContext, Depends(get_current_user_with_roles)] = None,
    session: Session = Depends(get_db_session),
):
    """List the permission set granted to a user in the current tenant."""
    user = UserRepository(session).get_by_tenant(current_user.tenant_id, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    permissions = {
        permission.id: permission
        for assignment in UserRoleRepository(session).get_user_roles(
            str(user_id), str(current_user.tenant_id)
        )
        for permission in assignment.role.permissions
    }
    return [PermissionResponse.model_validate(permission) for permission in permissions.values()]
