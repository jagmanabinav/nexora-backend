"""Security utilities for authentication and authorization."""

import os
import secrets
import base64
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.core.exceptions import AuthenticationException

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ============ ENCRYPTION FOR SENSITIVE DATA ============

class SecretEncryptor:
    """Encrypt and decrypt sensitive data like OAuth secrets, API keys, etc."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for encryptor"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the encryptor with a key derived from ENCRYPTION_KEY env var."""
        if self._initialized:
            return
        
        encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if not encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY environment variable must be set for secret encryption. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        # Ensure the key is valid base64-encoded 32 bytes for Fernet
        try:
            self.key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
            # Validate it's proper Fernet key format
            Fernet(self.key)
        except Exception:
            raise ValueError(
                "Invalid ENCRYPTION_KEY format. Must be a valid Fernet key. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        self.cipher = Fernet(self.key)
        self._initialized = True
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return base64-encoded ciphertext."""
        if not plaintext:
            return None
        
        try:
            ciphertext = self.cipher.encrypt(plaintext.encode())
            return base64.b64encode(ciphertext).decode()
        except Exception as e:
            raise ValueError(f"Failed to encrypt secret: {str(e)}")
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext string."""
        if not ciphertext:
            return None
        
        try:
            decoded = base64.b64decode(ciphertext.encode())
            plaintext = self.cipher.decrypt(decoded)
            return plaintext.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt secret: {str(e)}")


def get_encryptor() -> SecretEncryptor:
    """Get or create the secret encryptor instance."""
    return SecretEncryptor()


def generate_secure_secret(length: int = 32) -> str:
    """Generate a cryptographically secure random secret."""
    return secrets.token_urlsafe(length)


def mask_secret_for_logging(secret: str, visible_chars: int = 4) -> str:
    """
    Mask a secret for safe logging/display.
    
    Shows only the last N characters, rest masked with asterisks.
    """
    if not secret or len(secret) <= visible_chars:
        return "*" * len(secret) if secret else None
    
    return "*" * (len(secret) - visible_chars) + secret[-visible_chars:]


# ============ PASSWORD & TOKEN FUNCTIONS ============


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {**subject, "exp": expire, "type": "access"}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    subject: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {**subject, "exp": expire, "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str, token_type: str = "access") -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != token_type:
            raise AuthenticationException("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationException("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationException(f"Invalid token: {str(e)}")


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{secrets.token_hex(12)}"
