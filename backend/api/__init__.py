from fastapi import APIRouter
from core.config import settings
from .user.controller import router as user_router
from .admin.controller import router as admin_router

api_router = APIRouter()

if settings.DEBUG:
    from .debug.controller import router as debug_router
    api_router.include_router(debug_router, prefix="/debug")

# Add new API modules below.
api_router.include_router(user_router, prefix="/user")
api_router.include_router(admin_router, prefix="/admin")