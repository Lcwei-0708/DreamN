from fastapi import Request
from utils import get_real_ip
import redis.asyncio as aioredis
from core.config import settings
from utils.custom_exception import ServerException
from .schema import IPDebugResponse, ClearBlockedIPsResponse

async def get_ip_debug_info(request: Request) -> IPDebugResponse:
    try:
        return IPDebugResponse(
            client_host=request.client.host if request.client else None,
            x_forwarded_for=request.headers.get("x-forwarded-for"),
            x_real_ip=request.headers.get("x-real-ip"),
            detected_real_ip=get_real_ip(request)
        )
    except Exception as e:
        raise ServerException(f"Failed to get IP debug info: {e}")

async def clear_blocked_ips() -> ClearBlockedIPsResponse:
    try:
        redis = await aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        keys = await redis.keys("block:*")
        cleared = []
        if keys:
            for key in keys:
                await redis.delete(key)
                cleared.append(key.replace("block:", ""))
        return ClearBlockedIPsResponse(cleared_ips=cleared, count=len(cleared))
    except Exception as e:
        raise ServerException(f"Failed to clear blocked IPs: {e}")

async def clear_all_ws_connections():
    try:
        redis = await aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        online_users_keys = await redis.keys("ws:online_users*")
        userinfo_keys = await redis.keys("ws:userinfo:*")
        all_keys = online_users_keys + userinfo_keys
        cleared = []
        if all_keys:
            for key in all_keys:
                await redis.delete(key)
                cleared.append(key)
        await redis.delete("ws:online_users")
        cleared.append("ws:online_users")
        return {"cleared_keys": cleared, "count": len(cleared)}
    except Exception as e:
        raise ServerException(f"Failed to clear all ws connections: {e}")