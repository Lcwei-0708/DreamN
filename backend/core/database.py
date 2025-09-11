import logging
from core.config import settings
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import ASYNCHRONOUS
from influxdb_client.client.query_api import QueryApi

logger = logging.getLogger(__name__)

def make_async_url(url: str) -> str:
    if url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+aiomysql://", 1)
    if url.startswith("mysql+pymysql://"):
        return url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
    return url

# Async engine/session for API
async_engine = create_async_engine(
    make_async_url(settings.DATABASE_URL),
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_size=settings.DB_POOL_SIZE,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    max_overflow=settings.DB_MAX_OVERFLOW,
    connect_args={
        "charset": "utf8mb4",
    }
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)

# Sync engine/session for migration and schedule
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_size=settings.DB_POOL_SIZE,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    max_overflow=settings.DB_MAX_OVERFLOW,
    connect_args={
        "charset": "utf8mb4",
        "connect_timeout": settings.DB_CONNECT_TIMEOUT,
        "read_timeout": settings.DB_READ_TIMEOUT,
        "write_timeout": settings.DB_WRITE_TIMEOUT,
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

influxdb_client = None
influxdb_write_api = None
influxdb_query_api = None

def init_influxdb():
    """Initialize InfluxDB connection"""
    global influxdb_client, influxdb_write_api, influxdb_query_api
    
    try:
        influxdb_client = InfluxDBClient(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG,
            timeout=settings.INFLUXDB_TIMEOUT
        )
        
        influxdb_write_api = influxdb_client.write_api(write_options=ASYNCHRONOUS)
        influxdb_query_api = influxdb_client.query_api()
        
        logger.info("InfluxDB initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize InfluxDB: {e}")
        return False

def get_influxdb():
    """Get InfluxDB client"""
    global influxdb_client, influxdb_write_api, influxdb_query_api
    
    if influxdb_client is None:
        init_influxdb()
    
    return {
        "client": influxdb_client,
        "write_api": influxdb_write_api,
        "query_api": influxdb_query_api
    }

def init_db():
    """
    Initialize the database (create tables).
    Call this function at startup if you want to auto-create tables.
    """
    init_influxdb()
    pass