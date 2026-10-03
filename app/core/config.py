import os
from enum import Enum
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False

    # Application
    APP_NAME: str = "Nexora Core"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://nexora_user:nexora_password@localhost:5432/nexora_platform_db"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT - CRITICAL: Must be set via environment variable, no default
    JWT_SECRET: str = None  # Set to None to require explicit configuration
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate JWT_SECRET at initialization
        if not self.JWT_SECRET:
            raise ValueError(
                "JWT_SECRET must be set via JWT_SECRET environment variable. "
                "Use a strong, random secret with at least 32 characters (256 bits) for HS256. "
                "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        if len(self.JWT_SECRET) < 32:
            raise ValueError(
                f"JWT_SECRET must be at least 32 characters long for HS256 security. "
                f"Current length: {len(self.JWT_SECRET)}. "
                f"Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True


def get_settings() -> Settings:
    return Settings()
