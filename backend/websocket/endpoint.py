import json
import logging
from typing import Annotated
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends
from core.redis import get_redis
from extensions.keycloak import get_keycloak
from .manager import get_manager, ConnectionManager

router = APIRouter()
logger = logging.getLogger(__name__)

REDIS_ONLINE_USERS_KEY = "ws:online_users"

@router.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket,
    ws_manager: Annotated[ConnectionManager, Depends(get_manager)]
):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    keycloak = get_keycloak()
    try:
        userinfo = keycloak.keycloak_openid.userinfo(token)
        if not userinfo:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    sid = await ws_manager.connect(websocket, userinfo)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except Exception:
                msg = {}

            # Handle client-sent ping (client active heartbeat)
            if isinstance(msg, dict) and msg.get("type") == "ping":
                await ws_manager.update_heartbeat(sid, "ping")
                await websocket.send_text(json.dumps({"type": "pong"}))
                logger.info(f"Received ping from {userinfo.get('sub', 'unknown user')}")
                continue
            
            # Handle client-sent pong (response to server ping)
            if isinstance(msg, dict) and msg.get("type") == "pong":
                await ws_manager.update_heartbeat(sid, "pong")
                logger.info(f"Received pong from {userinfo.get('sub', 'unknown user')}")
                continue

            logger.info(f"Received from {userinfo.get('sub', 'unknown user')}: {data}")
            await ws_manager.broadcast("message", f"{userinfo.get('sub', 'unknown user')} says: {data}")
    except WebSocketDisconnect:
        await ws_manager.disconnect(sid)