"""API v1 router."""

from fastapi import APIRouter

from app.api.v1 import auth, rbac, applications, billing, advanced

router = APIRouter()

# Include sub-routers
router.include_router(auth.router)
router.include_router(rbac.router)
router.include_router(applications.router)
router.include_router(billing.router)
router.include_router(advanced.router)


@router.get("/")
async def root():
    return {
        "message": "Welcome to Nexora Core API v1",
        "status": "running",
    }
