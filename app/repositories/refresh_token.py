"""Refresh token repository for data access."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Repository for refresh token data access."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by token string."""
        return self.db.query(RefreshToken).filter(RefreshToken.token == token).first()

    def get_active_by_token(self, token: str) -> Optional[RefreshToken]:
        """Get active (non-revoked, non-expired) refresh token."""
        now = datetime.now(timezone.utc)
        return self.db.query(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > now
        ).first()

    def create(
        self,
        user_id: UUID,
        tenant_id: UUID,
        token: str,
        expires_at: datetime
    ) -> RefreshToken:
        """Create a new refresh token."""
        refresh_token = RefreshToken(
            user_id=user_id,
            tenant_id=tenant_id,
            token=token,
            expires_at=expires_at
        )
        self.db.add(refresh_token)
        self.db.flush()
        return refresh_token

    def revoke(self, token_id: UUID) -> bool:
        """Revoke a refresh token."""
        token = self.db.query(RefreshToken).filter(RefreshToken.id == token_id).first()
        if not token:
            return False
        token.is_revoked = True
        token.revoked_at = datetime.now(timezone.utc)
        self.db.flush()
        return True

    def revoke_by_token(self, token: str) -> bool:
        """Revoke refresh token by token string."""
        refresh_token = self.get_by_token(token)
        if not refresh_token:
            return False
        return self.revoke(refresh_token.id)

    def revoke_all_for_user(self, user_id: UUID) -> int:
        """Revoke all refresh tokens for a user."""
        tokens = self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).all()
        count = len(tokens)
        now = datetime.now(timezone.utc)
        for token in tokens:
            token.is_revoked = True
            token.revoked_at = now
        self.db.flush()
        return count

    def cleanup_expired(self) -> int:
        """Delete expired tokens."""
        now = datetime.now(timezone.utc)
        tokens = self.db.query(RefreshToken).filter(
            RefreshToken.expires_at < now
        ).all()
        count = len(tokens)
        for token in tokens:
            self.db.delete(token)
        self.db.flush()
        return count
