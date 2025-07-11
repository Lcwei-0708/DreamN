from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from utils import get_real_ip
from core.redis import get_redis
from core.config import settings

FAIL_LIMIT = settings.FAIL_LIMIT
FAIL_WINDOW = settings.FAIL_WINDOW
BLOCK_TIME = settings.BLOCK_TIME

class AuthRateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Only count 401 and 403
        if response.status_code in (401, 403):
            redis = get_redis()
            ip = get_real_ip(request)
            block_key = f"block:{ip}"
            fail_key = f"fail:{ip}"
            fails = await redis.incr(fail_key)
            print(f"IP {ip} fail count: {fails}")
            if fails == 1:
                await redis.expire(fail_key, FAIL_WINDOW)
            if fails >= FAIL_LIMIT:
                print(f"IP {ip} is now blocked")
                await redis.set(block_key, 1, ex=BLOCK_TIME)
                await redis.delete(fail_key)
        return response

def add_auth_rate_limiter_middleware(app):
    app.add_middleware(AuthRateLimiterMiddleware)