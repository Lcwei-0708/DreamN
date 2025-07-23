import pytest
import asyncio
import pytest_asyncio
from main import app
from core.config import settings
from core.dependencies import get_db
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch, Mock, MagicMock
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
    
    mock.smembers.return_value = set()
    mock.hgetall.return_value = {}
    mock.get.return_value = None
    mock.sadd.return_value = True
    mock.srem.return_value = True
    mock.hset.return_value = True
    mock.hdel.return_value = True
    mock.hlen.return_value = 0
    
    return mock


@pytest_asyncio.fixture
async def mock_modbus():
    """
    Provide a mock ModbusManager instance for testing
    """
    mock = AsyncMock()
    
    # Mock client management
    mock.clients = {}
    mock.client_status = {}
    mock._initialized = False
    mock.controller_mapping = {}
    
    # Define connection failure conditions
    def should_fail_connection(host, port):
        """Determine if connection should fail based on host and port"""
        # Specific IP range to simulate connection failure (e.g., 192.168.1.100-200)
        if host.startswith("192.168.1") and 100 <= int(host.split(".")[-1]) <= 200:
            return True
        
        # Specific port range to simulate connection failure (e.g., port 1000-2000)
        if 1000 <= port <= 2000:
            return True
        
        # Specific host names to simulate connection failure
        if host in ["failed-host.local", "unreachable.example.com"]:
            return True
        
        # Specific IPs to simulate connection failure
        if host in ["192.168.1.254", "10.0.0.1"]:
            return True
        
        return False
    
    # Mock create_tcp method
    def mock_create_tcp(host, port, timeout=30):
        client_id = f"tcp_{host}_{port}"
        mock_client = MagicMock()
        
        # Determine connection status based on conditions
        if should_fail_connection(host, port):
            mock_client.connected = False
            mock_client.is_socket_open.return_value = False
            mock.clients[client_id] = mock_client
            mock.client_status[client_id] = False
        else:
            mock_client.connected = True
            mock_client.is_socket_open.return_value = True
            mock.clients[client_id] = mock_client
            mock.client_status[client_id] = True
        
        return client_id
    
    mock.create_tcp.side_effect = mock_create_tcp
    
    # Mock connect method - determine success based on client_id
    async def mock_connect(client_id):
        # Parse host and port from client_id
        # client_id format: "tcp_host_port"
        try:
            parts = client_id.split("_")
            if len(parts) >= 3:
                host = parts[1]
                port = int(parts[2])
                should_fail = should_fail_connection(host, port)
                return not should_fail
        except (ValueError, IndexError):
            pass
        
        # Default to successful connection
        return True
    
    mock.connect = mock_connect
    
    # Mock disconnect method
    mock.disconnect.return_value = None
    
    # Mock is_healthy method
    mock.is_healthy.return_value = True
    
    # Mock read operations
    def mock_read_point_data(host, port, point_type, address, length, unit_id, data_type, formula=None, min_value=None, max_value=None):
        # If connection fails, raise exception
        if should_fail_connection(host, port):
            raise Exception("Connection failed")
        
        return {
            "raw_data": [1234],
            "converted_value": 1234,
            "final_value": 123.4,
            "data_type": "uint16",
            "read_time": "2024-01-01T10:00:00+00:00",
            "range_valid": True,
            "range_message": None,
            "min_value": 0.0,
            "max_value": 1000.0
        }
    
    mock.read_point_data.side_effect = mock_read_point_data
    
    # Mock write operations
    def mock_write_point_data(host, port, point_type, address, value, unit_id, data_type, formula=None, min_value=None, max_value=None):
        # If connection fails, raise exception
        if should_fail_connection(host, port):
            raise Exception("Connection failed")
        
        return {
            "write_value": value,
            "raw_data": [value] if isinstance(value, (int, float)) else [1 if value else 0],
            "write_time": "2024-01-01T10:00:00+00:00",
            "success": True
        }
    
    mock.write_point_data.side_effect = mock_write_point_data
    
    # Mock read_modbus_data method
    def mock_read_modbus_data(client_id, point_type, address, count, unit_id):
        # Parse host and port from client_id
        try:
            parts = client_id.split("_")
            if len(parts) >= 3:
                host = parts[1]
                port = int(parts[2])
                if should_fail_connection(host, port):
                    raise Exception("Connection failed")
        except (ValueError, IndexError):
            pass
        
        if point_type in ["coil", "input"]:
            return [True, False] * (count // 2) + ([True] if count % 2 else [])
        else:
            return [1234, 5678][:count]
    
    mock.read_modbus_data.side_effect = mock_read_modbus_data
    
    # Mock write_modbus_data method
    def mock_write_modbus_data(client_id, point_type, address, value, unit_id):
        # Parse host and port from client_id
        try:
            parts = client_id.split("_")
            if len(parts) >= 3:
                host = parts[1]
                port = int(parts[2])
                if should_fail_connection(host, port):
                    raise Exception("Connection failed")
        except (ValueError, IndexError):
            pass
        
        if point_type == "coil":
            return [value]
        else:
            return [int(value)]
    
    mock.write_modbus_data.side_effect = mock_write_modbus_data
    
    return mock


@pytest_asyncio.fixture
async def client(test_db_session, mock_redis, mock_modbus):
    """
    Create a test HTTP client with database, Redis, and Modbus dependency overrides.
    """
    # Override the database dependency to use test session
    async def override_get_db():
        yield test_db_session
    
    # Apply the dependency overrides
    app.dependency_overrides[get_db] = override_get_db
    
    # Mock Keycloak for WebSocket tests
    mock_keycloak = Mock()
    mock_keycloak_admin = Mock()
    mock_keycloak_admin.get_users.return_value = []
    mock_keycloak_admin.get_realm_roles_of_user.return_value = []
    mock_keycloak.keycloak_admin = mock_keycloak_admin
    
    # Mock ModbusTcpClient to prevent real connections
    mock_tcp_client = MagicMock()
    mock_tcp_client.connected = True
    mock_tcp_client.is_socket_open.return_value = True
    mock_tcp_client.connect.return_value = True
    mock_tcp_client.close.return_value = None
    
    # Mock read operations for ModbusTcpClient
    mock_read_result = MagicMock()
    mock_read_result.isError.return_value = False
    mock_read_result.bits = [True, False]
    mock_read_result.registers = [1234, 5678]
    
    mock_tcp_client.read_coils.return_value = mock_read_result
    mock_tcp_client.read_discrete_inputs.return_value = mock_read_result
    mock_tcp_client.read_holding_registers.return_value = mock_read_result
    mock_tcp_client.read_input_registers.return_value = mock_read_result
    
    # Mock write operations for ModbusTcpClient
    mock_write_result = MagicMock()
    mock_write_result.isError.return_value = False
    
    mock_tcp_client.write_coil.return_value = mock_write_result
    mock_tcp_client.write_register.return_value = mock_write_result
    
    # Use patch to replace get_redis, get_keycloak, and get_modbus in all modules
    with patch('core.redis.get_redis', return_value=mock_redis), \
         patch('core.dependencies.get_redis', return_value=mock_redis), \
         patch('middleware.auth_rate_limiter.get_redis', return_value=mock_redis), \
         patch('main.get_redis', return_value=mock_redis), \
         patch('api.websocket.services.get_redis', return_value=mock_redis), \
         patch('websocket.manager.get_redis', return_value=mock_redis), \
         patch('websocket.endpoint.get_redis', return_value=mock_redis), \
         patch('extensions.keycloak.get_keycloak', return_value=mock_keycloak), \
         patch('websocket.manager.get_keycloak', return_value=mock_keycloak), \
         patch('extensions.modbus.get_modbus', return_value=mock_modbus), \
         patch('api.modbus.controller.get_modbus', return_value=mock_modbus), \
         patch('api.modbus.services.ModbusManager', return_value=mock_modbus), \
         patch('extensions.modbus.ModbusManager', return_value=mock_modbus), \
         patch('pymodbus.client.ModbusTcpClient', return_value=mock_tcp_client), \
         patch('extensions.modbus.ModbusTcpClient', return_value=mock_tcp_client):
        
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