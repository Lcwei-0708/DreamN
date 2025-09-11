import logging
from core.redis import get_redis
from utils import get_real_ip
from utils.response import APIResponse
from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import AsyncSessionLocal, SessionLocal, get_influxdb

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

# InfluxDB dependency
def get_influxdb_client():
    try:
        influxdb = get_influxdb()
        yield influxdb
    except Exception as e:
        logger.error(f"InfluxDB error: {e}")
        raise e