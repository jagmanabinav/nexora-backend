"""Tenant user provisioning schemas."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator
from typing import Annotated

from app.schemas.auth import UserResponse


class TenantUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    first_name: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    last_name: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    role_id: Optional[UUID] = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        return value


class TenantUserItem(BaseModel):
    user: UserResponse
    role_id: UUID
    role_name: str


class TenantUsersResponse(BaseModel):
    users: List[TenantUserItem]
    roles: list[dict]
    plan_name: str
    max_users: int
    user_count: int
