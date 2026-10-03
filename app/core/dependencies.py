"""Application dependencies for FastAPI."""

from typing import Annotated, Generator, Optional, List
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthenticationException
from app.core.security import decode_token, generate_request_id
from app.database.connection import get_db


async def get_request_id(
    x_request_id: Annotated[str | None, Header()] = None,
) -> str:
    """Get or generate a request ID."""
    return x_request_id or generate_request_id()


def get_db_session() -> Generator[Session, None, None]:
    """Get a database session."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


class RequestContext:
    """Request context with authentication info."""

    def __init__(
        self,
        user_id: UUID,
        tenant_id: UUID,
        email: str,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email
        self.roles = roles or []
        self.permissions = permissions or []

    def has_permission(self, permission_code: str) -> bool:
        """Check if user has a permission."""
        return permission_code in self.permissions

    def has_role(self, role_name: str) -> bool:
        """Check if user has a role."""
        return role_name in self.roles


async def get_current_user(
    authorization: Annotated[str, Header()] = None,
) -> RequestContext:
    """Get current user from JWT token (without roles/permissions)."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    try:
        payload = decode_token(token, token_type="access")
        user_id = UUID(payload.get("sub"))
        tenant_id = UUID(payload.get("tenant_id"))
        email = payload.get("email")

        if not all([user_id, tenant_id, email]):
            raise AuthenticationException("Invalid token payload")

        return RequestContext(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_with_roles(
    authorization: Annotated[str, Header()] = None,
    session: Session = Depends(get_db_session),
) -> RequestContext:
    """Get current user with roles and permissions from JWT token."""
    context = await get_current_user(authorization)

    # Fetch user roles and permissions from database
    from app.repositories.user_role import UserRoleRepository

    user_role_repo = UserRoleRepository(session)
    user_roles = user_role_repo.get_user_roles(str(context.user_id), str(context.tenant_id))

    roles = []
    permissions = set()

    for user_role in user_roles:
        role = user_role.role
        roles.append(role.name)

        # Collect permissions from role
        for permission in role.permissions:
            permissions.add(permission.code)

    context.roles = roles
    context.permissions = list(permissions)

    return context


async def get_request_context(
    authorization: Annotated[str, Header()] = None,
    session: Session = Depends(get_db_session),
) -> RequestContext:
    """Get request context with current user and their roles/permissions."""
    return await get_current_user_with_roles(authorization, session)
