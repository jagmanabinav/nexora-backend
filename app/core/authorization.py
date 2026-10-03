"""
Authorization decorators for RBAC.

Provides authorization checks for endpoints based on roles and permissions.
"""

from typing import Callable, List, Optional
from functools import wraps
from fastapi import HTTPException, status

from app.core.dependencies import RequestContext
from app.core.exceptions import AuthorizationException


def require_permission(permission_codes: List[str]):
    """Decorator to require one or more permissions.
    
    User must have at least one of the specified permissions.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: RequestContext = None, **kwargs):
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            has_permission = any(
                current_user.has_permission(code) for code in permission_codes
            )

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator


def require_role(role_names: List[str]):
    """Decorator to require one or more roles.
    
    User must have at least one of the specified roles.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: RequestContext = None, **kwargs):
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            has_role = any(current_user.has_role(role) for role in role_names)

            if not has_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator
