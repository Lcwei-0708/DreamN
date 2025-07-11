import logging
from fastapi import APIRouter, Request, HTTPException
from utils.response import APIResponse, parse_responses
from .services import get_ip_debug_info, clear_blocked_ips, clear_all_ws_connections
from .schema import IPDebugResponse, ClearBlockedIPsResponse, ClearWSConnectionsResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["debug"])

@router.get("/test-ip", 
            response_model=APIResponse[IPDebugResponse],
            summary="Test IP detection",
            responses=parse_responses({
                200: ("IP detection successful", IPDebugResponse),
                400: ("Invalid IP address", None),
                500: ("Internal Server Error", None),
            })
)
async def test_ip_detection(request: Request):
    try:
        result = await get_ip_debug_info(request)
        return APIResponse(
            code=200,
            message="IP detection successful",
            data=result
        )
    except Exception:
        raise HTTPException(status_code=500)

@router.delete(
    "/clear-blocked-ip",
    summary="Clear all blocked IPs in Redis",
    response_model=APIResponse[ClearBlockedIPsResponse],
    responses=parse_responses({
        200: ("Blocked IPs cleared successfully", ClearBlockedIPsResponse),
        500: ("Internal Server Error", None),
    })
)
async def clear_blocked_ips_api():
    try:
        result = await clear_blocked_ips()
        return APIResponse(
            code=200,
            message="Blocked IPs cleared successfully",
            data=result
        )
    except Exception:
        raise HTTPException(status_code=500)

@router.delete(
    "/clear-ws-connections",
    summary="Clear all WebSocket connections (Redis)",
    response_model=APIResponse[ClearWSConnectionsResponse],
    responses=parse_responses({
        200: ("WebSocket connections cleared successfully", ClearWSConnectionsResponse),
        500: ("Internal Server Error", None),
    })
)
async def clear_ws_connections_api():
    try:
        result = await clear_all_ws_connections()
        return APIResponse(
            code=200,
            message="WebSocket connections cleared successfully",
            data=result
        )
    except Exception:
        raise HTTPException(status_code=500)