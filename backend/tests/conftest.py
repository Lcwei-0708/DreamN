import pytest
import asyncio
import pytest_asyncio
from main import app
from core.config import settings
from core.dependencies import get_db
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from core.database import Base, make_async_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """
    Create an isolated database engine for each test.
    Uses optimized connection settings for testing.
    """
    engine = create_async_engine(
        make_async_url(settings.DATABASE_URL_TEST),
        echo=False,
        future=True,
        poolclass=StaticPool,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={
            "charset": "utf8mb4",
            "autocommit": False,
        }
    )
    
    # Create all tables for testing
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup: drop all tables and dispose engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_engine):
    """
    Create an isolated database session for each test.
    Automatically handles transaction rollback after each test.
    """
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )
    
    async with TestSessionLocal() as session:
        # Start a transaction that will be rolled back after the test
        transaction = await session.begin()
        try:
            yield session
        finally:
            # Check if transaction is still active before rollback
            try:
                if transaction.is_active:
                    await transaction.rollback()
            except Exception:
                # Transaction might already be closed, ignore the error
                pass


@pytest_asyncio.fixture
async def mock_redis():
    """
    Provide a mock Redis instance to avoid real Redis connection issues
    """
    mock = AsyncMock()
    # Set default return values for common Redis methods
    mock.exists.return_value = False
    mock.incr.return_value = 1
    mock.expire.return_value = True
    mock.keys.return_value = []
    mock.delete.return_value = 0
    mock.set.return_value = True
    mock.close.return_value = None
    
    return mock


@pytest_asyncio.fixture
async def client(test_db_session, mock_redis):
    """
    Create a test HTTP client with database and Redis dependency overrides.
    """
    # Override the database dependency to use test session
    async def override_get_db():
        yield test_db_session
    
    # Apply the dependency overrides
    app.dependency_overrides[get_db] = override_get_db
    
    from unittest.mock import Mock
    mock_keycloak = Mock()
    mock_keycloak_admin = Mock()
    mock_keycloak_admin.get_users.return_value = []  # No users
    mock_keycloak_admin.get_realm_roles_of_user.return_value = []  # No roles
    mock_keycloak.keycloak_admin = mock_keycloak_admin
    
    # Use patch to replace get_redis and get_keycloak in all modules
    with patch('core.redis.get_redis', return_value=mock_redis), \
         patch('core.dependencies.get_redis', return_value=mock_redis), \
         patch('middleware.auth_rate_limiter.get_redis', return_value=mock_redis), \
         patch('main.get_redis', return_value=mock_redis), \
         patch('extensions.keycloak.get_keycloak', return_value=mock_keycloak):
        
        try:
            # Create HTTP client using ASGI transport
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, 
                base_url="http://testserver",
                timeout=30.0
            ) as ac:
                yield ac
        finally:
            # Always clean up dependency overrides
            app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def event_loop():
    """
    Create a session-scoped event loop for pytest-asyncio.
    This resolves event loop conflicts between httpx AsyncClient and database engine.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()