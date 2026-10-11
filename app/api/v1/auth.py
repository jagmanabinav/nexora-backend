"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import RequestContext, get_current_user, get_db_session, get_request_id
from app.core.exceptions import AuthenticationException, ConflictException, ValidationException
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserMeResponse,
    UserRegisterRequest,
    UserResponse,
    TenantResponse,
)
from app.schemas.rbac import RoleResponse
from app.schemas.response import SuccessResponse
from app.services.authentication import AuthenticationService

router = APIRouter(prefix="/auth", tags=["authentication"])


def require_company_application():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Instant registration is disabled. Submit a company application to register.",
    )


@router.post(
    "/register",
    response_model=SuccessResponse,
    responses={410: {"description": "Instant registration is disabled"}},
    dependencies=[Depends(require_company_application)],
)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db_session),
    request_id: str = Depends(get_request_id),
):
    """Register a new user and create tenant."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        auth_service = AuthenticationService(db)
        result = auth_service.register(
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            tenant_name=request.tenant_name,
            tenant_slug=request.tenant_slug,
        )
        db.commit()

        # Use model_validate instead of from_orm (Pydantic v2)
        user_response = UserResponse.model_validate(result["user"])
        tenant_response = TenantResponse.model_validate(result["tenant"])
        tokens = TokenResponse(**result["tokens"])

        return SuccessResponse(
            data={
                "user": user_response.model_dump(),
                "tenant": tenant_response.model_dump(),
                "tokens": tokens.model_dump(),
            },
            message="Registration successful",
            request_id=request_id,
        )
    except ConflictException as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationException as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        db.rollback()
        logger.exception(f"Registration failed for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=SuccessResponse)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db_session),
    request_id: str = Depends(get_request_id),
):
    """Login user and return tokens."""
    try:
        auth_service = AuthenticationService(db)
        result = auth_service.login(
            email=request.email,
            password=request.password,
        )

        user_response = UserResponse.model_validate(result["user"])
        tenant_response = TenantResponse.model_validate(result["tenant"])
        tokens = TokenResponse(**result["tokens"])

        return SuccessResponse(
            data={
                "user": user_response.model_dump(),
                "tenant": tenant_response.model_dump(),
                "tokens": tokens.model_dump(),
            },
            message="Login successful",
            request_id=request_id,
        )
    except AuthenticationException as e:
        if "Company registration" in str(e) or "Subscription expired" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )


@router.post("/refresh", response_model=SuccessResponse)
async def refresh(
    request: dict,
    db: Session = Depends(get_db_session),
    request_id: str = Depends(get_request_id),
):
    """Refresh access token using refresh token."""
    refresh_token = request.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token is required",
        )

    try:
        auth_service = AuthenticationService(db)
        result = auth_service.refresh(refresh_token)

        user_response = UserResponse.model_validate(result["user"])
        tokens = TokenResponse(**result["tokens"])

        return SuccessResponse(
            data={
                "user": user_response.model_dump(),
                "tokens": tokens.model_dump(),
            },
            message="Token refreshed successfully",
            request_id=request_id,
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
                if "Subscription expired" in str(e)
                else status.HTTP_401_UNAUTHORIZED
            ),
            detail=str(e) if "Subscription expired" in str(e) else "Token refresh failed",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed",
        )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: Annotated[RequestContext, Depends(get_current_user)],
    db: Session = Depends(get_db_session),
    request_id: str = Depends(get_request_id),
):
    """Logout user and revoke all refresh tokens."""
    try:
        auth_service = AuthenticationService(db)
        auth_service.logout(current_user.user_id, current_user.tenant_id)
        db.commit()

        return SuccessResponse(
            data={"message": "Logout successful"},
            message="Logged out successfully",
            request_id=request_id,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )


@router.get("/me", response_model=SuccessResponse)
async def get_current_user_info(
    current_user: Annotated[RequestContext, Depends(get_current_user)],
    db: Session = Depends(get_db_session),
    request_id: str = Depends(get_request_id),
):
    """Get current user info."""
    try:
        from app.repositories.user import UserRepository
        from app.repositories.tenant import TenantRepository

        user_repo = UserRepository(db)
        tenant_repo = TenantRepository(db)

        user = user_repo.get_by_id(current_user.user_id)
        if not user or user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        tenant = tenant_repo.get_by_id(current_user.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        from app.repositories.user_role import UserRoleRepository

        user_roles = UserRoleRepository(db).get_user_roles(
            str(current_user.user_id), str(current_user.tenant_id)
        )
        roles = [RoleResponse.model_validate(user_role.role).model_dump(mode="json") for user_role in user_roles]
        permissions = sorted(
            {
                permission.code
                for user_role in user_roles
                for permission in user_role.role.permissions
            }
        )

        user_response = UserResponse.model_validate(user)
        tenant_response = TenantResponse.model_validate(tenant)

        return SuccessResponse(
            data={
                "user": user_response.model_dump(),
                "tenant": tenant_response.model_dump(),
                "roles": roles,
                "permissions": permissions,
            },
            message="User info retrieved successfully",
            request_id=request_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user info",
        )
