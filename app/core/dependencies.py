"""Application dependencies for FastAPI."""

from typing import Annotated, Generator, Optional, List
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthenticationException
from app.core.security import decode_token, generate_request_id
from app.core.constants import TENANT_STATUS_ACTIVE, USER_STATUS_ACTIVE
from app.database.connection import get_db
from app.services.subscription_access import subscription_expired


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
        request_path: Optional[str] = None,
        request_method: Optional[str] = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email
        self.roles = roles or []
        self.permissions = permissions or []
        self.request_path = request_path
        self.request_method = request_method

    def has_permission(self, permission_code: str) -> bool:
        """Check if user has a permission."""
        return permission_code in self.permissions

    def has_role(self, role_name: str) -> bool:
        """Check if user has a role."""
        return role_name in self.roles


async def get_current_user(
    authorization: Annotated[str, Header()] = None,
    session: Session = Depends(get_db_session),
    request: Request = None,
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

        from app.repositories.tenant import TenantRepository
        from app.repositories.user import UserRepository

        user = UserRepository(session).get_by_tenant(tenant_id, user_id)
        tenant = TenantRepository(session).get_by_id(tenant_id)
        if (
            not user
            or not tenant
            or tenant.status != TENANT_STATUS_ACTIVE
            or user.status != USER_STATUS_ACTIVE
        ):
            raise AuthenticationException("Account is pending approval or inactive")
        renewal_paths = ("/api/v1/subscriptions", "/api/v1/plans")
        if (
            subscription_expired(session, tenant_id)
            and (request is None or not request.url.path.startswith(renewal_paths))
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscription expired. Renew your plan to continue.",
            )

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
    request: Request = None,
) -> RequestContext:
    """Get current user with roles and permissions from JWT token."""
    context = await get_current_user(authorization, session, request)

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
    request: Request,
    authorization: Annotated[str, Header()] = None,
    session: Session = Depends(get_db_session),
) -> RequestContext:
    """Get request context with current user and their roles/permissions."""
    context = await get_current_user_with_roles(authorization, session, request)
    context.request_path = request.url.path
    context.request_method = request.method
    return context
