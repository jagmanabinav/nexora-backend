"""Authentication service for handling auth logic."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AuthenticationException,
    ConflictException,
    ResourceNotFoundException,
    ValidationException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.core.constants import (
    TENANT_STATUS_ACTIVE,
    TENANT_STATUS_PENDING,
    TENANT_STATUS_REJECTED,
    USER_STATUS_ACTIVE,
)
from app.core.permissions import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from app.repositories.permission import PermissionRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.role import RoleRepository
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.repositories.user_role import UserRoleRepository
from app.services.subscription_access import subscription_expired


class AuthenticationService:
    """Service for authentication operations."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.tenant_repo = TenantRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)

    def register(
        self,
        email: str,
        password: str,
        first_name: Optional[str],
        last_name: Optional[str],
        tenant_name: str,
        tenant_slug: str,
        tenant_status: str = TENANT_STATUS_ACTIVE,
        tenant_email: Optional[str] = None,
        tenant_phone: Optional[str] = None,
        issue_tokens: bool = True,
    ) -> dict:
        """Register a new user and create tenant."""
        if tenant_slug == "nexora-platform":
            raise ConflictException("Tenant slug 'nexora-platform' is reserved")

        # Check if tenant slug already exists
        existing_tenant = self.tenant_repo.get_by_slug(tenant_slug)
        if existing_tenant:
            raise ConflictException(f"Tenant slug '{tenant_slug}' already exists")

        # Check if email already exists globally
        existing_user = self.user_repo.get_by_email(email)
        if existing_user:
            raise ConflictException(f"Email '{email}' already registered")

        # Create tenant
        tenant = self.tenant_repo.create(
            name=tenant_name,
            slug=tenant_slug,
            email=tenant_email,
            phone=tenant_phone,
        )
        tenant.status = tenant_status

        # Hash password and create user
        password_hash = hash_password(password)
        user = self.user_repo.create(
            tenant_id=tenant.id,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name
        )

        permission_repo = PermissionRepository(self.db)
        role_repo = RoleRepository(self.db)
        tenant_roles = {}
        for role_key in ("admin", "manager", "member"):
            role_config = DEFAULT_ROLES[role_key]
            role_permissions = []
            for code in role_config["permissions"]:
                permission = permission_repo.get_by_code(code)
                if permission is None:
                    permission = permission_repo.create(code, DEFAULT_PERMISSIONS[code])
                role_permissions.append(permission)

            tenant_role = role_repo.create(
                str(tenant.id),
                role_config["name"],
                role_config["description"],
            )
            tenant_role.permissions = role_permissions
            tenant_roles[role_key] = tenant_role

        UserRoleRepository(self.db).assign(
            str(user.id), str(tenant_roles["admin"].id), str(tenant.id)
        )

        tokens = self._generate_tokens(user) if issue_tokens else None

        return {
            "user": user,
            "tenant": tenant,
            "tokens": tokens
        }

    def login(self, email: str, password: str) -> dict:
        """Authenticate user and return tokens."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Find user by email
        logger.debug(f"Attempting login for email: {email}")
        user = self.user_repo.get_by_email(email)
        if not user:
            logger.error(f"User not found for email: {email}")
            raise AuthenticationException("Invalid email or password")

        logger.debug(f"User found: {user.id}, checking password")
        # Verify password
        if not verify_password(password, user.password_hash):
            logger.error(f"Password verification failed for user: {email}")
            raise AuthenticationException("Invalid email or password")

        logger.debug(f"Password verified for user: {email}")
        # Get tenant
        tenant = self.tenant_repo.get_by_id(user.tenant_id)
        if not tenant:
            logger.error(f"Tenant not found: {user.tenant_id}")
            raise ResourceNotFoundException("Tenant", user.tenant_id)
        if tenant.status == TENANT_STATUS_PENDING:
            raise AuthenticationException("Company registration is awaiting Super Admin approval")
        if tenant.status == TENANT_STATUS_REJECTED:
            raise AuthenticationException("Company registration was not approved")
        if tenant.status != TENANT_STATUS_ACTIVE or user.status != USER_STATUS_ACTIVE:
            raise AuthenticationException("Account is inactive")
        if subscription_expired(self.db, tenant.id):
            raise AuthenticationException(
                "Subscription expired. Renew your plan to continue."
            )

        # Generate tokens
        tokens = self._generate_tokens(user)

        # Update last login
        self.user_repo.update(user.id, last_login_at=datetime.now(timezone.utc))
        self.db.commit()

        logger.debug(f"Login successful for user: {email}")
        return {
            "user": user,
            "tenant": tenant,
            "tokens": tokens
        }

    def refresh(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token."""
        # Verify and decode refresh token
        try:
            payload = decode_token(refresh_token, token_type="refresh")
        except AuthenticationException as e:
            raise AuthenticationException(f"Invalid refresh token: {str(e)}")

        user_id = UUID(payload.get("sub"))
        tenant_id = UUID(payload.get("tenant_id"))

        # Get user
        user = self.user_repo.get_by_tenant(tenant_id, user_id)
        if not user:
            raise AuthenticationException("User not found or tenant mismatch")
        tenant = self.tenant_repo.get_by_id(tenant_id)
        if (
            not tenant
            or tenant.status != TENANT_STATUS_ACTIVE
            or user.status != USER_STATUS_ACTIVE
        ):
            raise AuthenticationException("Account is pending approval or inactive")
        if subscription_expired(self.db, tenant_id):
            raise AuthenticationException(
                "Subscription expired. Renew your plan to continue."
            )

        # Verify refresh token is active in database
        token_record = self.refresh_token_repo.get_active_by_token(refresh_token)
        if not token_record:
            raise AuthenticationException("Refresh token is invalid or expired")

        # Revoke old refresh token
        self.refresh_token_repo.revoke_by_token(refresh_token)

        # Generate new tokens (rotation)
        new_tokens = self._generate_tokens(user)

        self.db.commit()

        return {
            "user": user,
            "tokens": new_tokens
        }

    def logout(self, user_id: UUID, tenant_id: UUID) -> bool:
        """Logout user by revoking all refresh tokens."""
        # Verify user belongs to tenant
        user = self.user_repo.get_by_tenant(tenant_id, user_id)
        if not user:
            raise AuthenticationException("User not found or tenant mismatch")

        # Revoke all refresh tokens
        self.refresh_token_repo.revoke_all_for_user(user_id)
        self.db.commit()

        return True

    def _generate_tokens(self, user: User) -> dict:
        """Generate access and refresh tokens."""
        from app.core.config import get_settings
        settings = get_settings()

        # Create access token
        access_token = create_access_token({
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email
        })

        # Create refresh token
        refresh_token_str = create_refresh_token({
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email
        })

        # Store refresh token in database
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        self.refresh_token_repo.create(
            user_id=user.id,
            tenant_id=user.tenant_id,
            token=refresh_token_str,
            expires_at=expires_at
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
