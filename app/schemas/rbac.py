"""
Schemas for RBAC operations.

Validates request/response data for role and permission endpoints.
"""

from typing import List, Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, StringConstraints


class PermissionResponse(BaseModel):
    """Permission response schema."""

    id: str
    code: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    """Schema for creating a role."""

    name: Annotated[str, StringConstraints(min_length=1, max_length=100)] = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")


class RoleUpdate(BaseModel):
    """Schema for updating a role."""

    name: Optional[Annotated[str, StringConstraints(min_length=1, max_length=100)]] = Field(
        None, description="Role name"
    )
    description: Optional[str] = Field(None, description="Role description")


class RoleResponse(BaseModel):
    """Role response schema."""

    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    status: str
    permissions: List[PermissionResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleDetailResponse(RoleResponse):
    """Detailed role response with permissions."""

    user_count: Optional[int] = None


class RolePermissionAssign(BaseModel):
    """Schema for assigning permissions to roles."""

    permission_ids: List[str] = Field(..., description="List of permission IDs to assign")


class UserRoleResponse(BaseModel):
    """User role response schema."""

    id: str
    user_id: str
    role_id: str
    role_name: Optional[str] = None
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True
