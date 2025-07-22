from fastapi import APIRouter
from core.config import settings
from .user.controller import router as user_router
from .admin.controller import router as admin_router
from .websocket.controller import router as websocket_router
from .webpush.controller import router as webpush_router
from .modbus.controller import router as modbus_router

api_router = APIRouter()

if settings.DEBUG:
    from .debug.controller import router as debug_router
    api_router.include_router(debug_router, prefix="/debug")

# Add new API modules below.
api_router.include_router(user_router, prefix="/user")
api_router.include_router(admin_router, prefix="/admin")
api_router.include_router(websocket_router, prefix="/websocket")
api_router.include_router(webpush_router, prefix="/webpush")
api_router.include_router(modbus_router, prefix="/modbus")