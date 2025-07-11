import logging
from core.redis import get_redis
from utils import get_real_ip
from utils.response import APIResponse
from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import AsyncSessionLocal, SessionLocal

logger = logging.getLogger(__name__)

# Async DB dependency
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"Database error: {e}")
            await db.rollback()
            raise e

# Sync DB dependency
def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

# Rate limit on auth fail
async def rate_limit_on_auth_fail(request: Request):
    redis = get_redis()
    ip = get_real_ip(request)
    block_key = f"block:{ip}"
    if await redis.exists(block_key):
        resp = APIResponse(code=429, message="Too many failed attempts. Try again later.", data=None)
        raise HTTPException(status_code=429, detail=resp.message)