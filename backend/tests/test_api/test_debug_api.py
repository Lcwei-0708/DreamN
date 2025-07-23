import pytest
from fastapi import Request
from utils.get_real_ip import get_real_ip
from unittest.mock import Mock, AsyncMock, patch
from starlette.datastructures import Address, Headers

class TestGetRealIP:
    """Tests for get_real_ip function"""
    
    def create_mock_request(self, headers=None, client_host="127.0.0.1"):
        """Create mock Request object"""
        request = Mock(spec=Request)
        request.headers = Headers(headers or {})
        request.client = Address(client_host, 8000) if client_host else None
        return request
    
    def test_get_real_ip_from_x_forwarded_for(self):
        """Test getting IP from X-Forwarded-For header"""
        request = self.create_mock_request({
            "x-forwarded-for": "192.168.1.100, 10.0.0.1, 172.16.0.1"
        })
        
        result = get_real_ip(request)
        assert result == "192.168.1.100"
    
    def test_get_real_ip_from_x_real_ip(self):
        """Test getting IP from X-Real-IP header"""
        request = self.create_mock_request({
            "x-real-ip": "203.0.113.45"
        })
        
        result = get_real_ip(request)
        assert result == "203.0.113.45"
    
    def test_get_real_ip_priority_forwarded_for_over_real_ip(self):
        """Test X-Forwarded-For priority over X-Real-IP"""
        request = self.create_mock_request({
            "x-forwarded-for": "192.168.1.100",
            "x-real-ip": "203.0.113.45"
        })
        
        result = get_real_ip(request)
        assert result == "192.168.1.100"
    
    def test_get_real_ip_fallback_to_client_host(self):
        """Test fallback to client.host"""
        request = self.create_mock_request({}, client_host="127.0.0.1")
        
        result = get_real_ip(request)
        assert result == "127.0.0.1"
    
    def test_get_real_ip_no_client(self):
        """Test case with no client information"""
        request = self.create_mock_request({}, client_host=None)
        
        result = get_real_ip(request)
        assert result == "unknown"
    
    def test_get_real_ip_strip_whitespace(self):
        """Test whitespace handling in IP strings"""
        request = self.create_mock_request({
            "x-forwarded-for": "  192.168.1.100  , 10.0.0.1"
        })
        
        result = get_real_ip(request)
        assert result == "192.168.1.100"


class TestClearBlockedIPs:
    """Tests for clear_blocked_ips function"""
    
    @pytest.mark.asyncio
    async def test_clear_blocked_ips_success(self):
        """Test successfully clearing blocked IPs"""
        from api.debug.services import clear_blocked_ips
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.keys.return_value = ["block:192.168.1.100", "block:10.0.0.1", "block:172.16.0.1"]
        mock_redis.delete = AsyncMock()
        
        # Mock aioredis.from_url to return a coroutine that resolves to mock_redis
        async def mock_from_url(*args, **kwargs):
            return mock_redis
        
        with patch("api.debug.services.aioredis.from_url", side_effect=mock_from_url):
            result = await clear_blocked_ips()
            
            # Verify Redis operations
            mock_redis.keys.assert_called_once_with("block:*")
            assert mock_redis.delete.call_count == 3
            
            # Verify return result
            assert result.count == 3
            assert set(result.cleared_ips) == {"192.168.1.100", "10.0.0.1", "172.16.0.1"}
    
    @pytest.mark.asyncio
    async def test_clear_blocked_ips_empty(self):
        """Test clearing when no blocked IPs exist"""
        from api.debug.services import clear_blocked_ips
        
        # Mock Redis with no keys
        mock_redis = AsyncMock()
        mock_redis.keys.return_value = []
        
        # Mock aioredis.from_url to return a coroutine that resolves to mock_redis
        async def mock_from_url(*args, **kwargs):
            return mock_redis
        
        with patch("api.debug.services.aioredis.from_url", side_effect=mock_from_url):
            result = await clear_blocked_ips()
            
            mock_redis.keys.assert_called_once_with("block:*")
            mock_redis.delete.assert_not_called()
            
            assert result.count == 0
            assert result.cleared_ips == []
    
    @pytest.mark.asyncio
    async def test_clear_blocked_ips_single_ip(self):
        """Test clearing single blocked IP"""
        from api.debug.services import clear_blocked_ips
        
        # Mock Redis with single key
        mock_redis = AsyncMock()
        mock_redis.keys.return_value = ["block:203.0.113.45"]
        mock_redis.delete = AsyncMock()
        
        # Mock aioredis.from_url to return a coroutine that resolves to mock_redis
        async def mock_from_url(*args, **kwargs):
            return mock_redis
        with patch("api.debug.services.aioredis.from_url", side_effect=mock_from_url):
            result = await clear_blocked_ips()
            
            # Verify Redis operations
            mock_redis.keys.assert_called_once_with("block:*")
            mock_redis.delete.assert_called_once_with("block:203.0.113.45")
            
            # Verify return result
            assert result.count == 1
            assert result.cleared_ips == ["203.0.113.45"]