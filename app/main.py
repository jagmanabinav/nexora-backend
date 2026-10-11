"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all models to register them with SQLAlchemy
# This MUST happen before any database queries
from app.models import (
    user,
    tenant,
    tenant_application,
    role,
    permission,
    role_permission,
    user_role,
    application,
    invoice,
    subscription,
    payment_method,
    plan,
    refresh_token,
    oauth_provider,
    file_upload,
    audit_log,
    data_export,
    email_log,
    api_key,
    usage_record,
    webhook,
    fabwash_invoice,
)

from app.api.v1 import router as api_v1_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.middleware.error_handler import ExceptionHandlingMiddleware, RequestContextMiddleware

# Setup logging
setup_logging()

settings = get_settings()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    # Add middleware
    app.add_middleware(ExceptionHandlingMiddleware)
    app.add_middleware(RequestContextMiddleware)

    # Add CORS middleware
    cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_v1_router.router, prefix=settings.API_V1_PREFIX)

    # Health check endpoints
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    @app.get("/ready")
    async def readiness_check():
        # TODO: Add checks for database, redis, etc.
        return {
            "status": "ready",
            "service": settings.APP_NAME,
        }

    return app


app = create_app()
