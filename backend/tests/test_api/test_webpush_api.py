import pytest
from unittest.mock import AsyncMock, patch, MagicMock

MOCK_TOKEN = "mocktoken"
MOCK_USER_ID = "user_001"
MOCK_ROLE = "test_role"
MOCK_ENDPOINT = "https://example.com/1"
MOCK_KEYS = {"p256dh": "key", "auth": "auth"}
MOCK_USER_AGENT = "pytest-agent"
MOCK_SUB_ID = "subid1"

@pytest.mark.asyncio
async def test_subscribe(client):
    req = {
        "endpoint": MOCK_ENDPOINT,
        "keys": MOCK_KEYS,
        "user_agent": MOCK_USER_AGENT
    }
    
    # Create a mock keycloak instance
    mock_keycloak = MagicMock()
    mock_keycloak.verify_token = AsyncMock(return_value=True)
    
    with patch("api.webpush.controller.subscribe_webpush", AsyncMock(return_value={"id": MOCK_SUB_ID, "endpoint": MOCK_ENDPOINT})), \
         patch("core.security.get_keycloak", return_value=mock_keycloak):
        resp = await client.post("/api/webpush/subscribe", json=req, headers={"Authorization": f"Bearer {MOCK_TOKEN}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == MOCK_SUB_ID

@pytest.mark.asyncio
async def test_unsubscribe(client):
    req = {"endpoint": MOCK_ENDPOINT}
    
    # Create a mock keycloak instance
    mock_keycloak = MagicMock()
    mock_keycloak.verify_token = AsyncMock(return_value=True)
    
    with patch("api.webpush.controller.unsubscribe_webpush", AsyncMock(return_value=True)), \
         patch("core.security.get_keycloak", return_value=mock_keycloak):
        resp = await client.post("/api/webpush/unsubscribe", json=req, headers={"Authorization": f"Bearer {MOCK_TOKEN}"})
        assert resp.status_code == 200

@pytest.mark.asyncio
async def test_get_subscriptions(client):
    mock_result = {
        "total_users": 1,
        "total_subscriptions": 1,
        "users": [
            {
                "user_id": MOCK_USER_ID,
                "total_subscriptions": 1,
                "subscriptions": [
                    {
                        "id": MOCK_SUB_ID,
                        "endpoint": MOCK_ENDPOINT,
                        "keys": MOCK_KEYS,
                        "is_active": True,
                        "user_agent": MOCK_USER_AGENT,
                        "created_at": "2024-06-01T12:00:00+00:00",
                        "updated_at": "2024-06-01T12:05:00+00:00"
                    }
                ]
            }
        ]
    }
    with patch("api.webpush.controller.get_all_webpush_subscriptions", AsyncMock(return_value=mock_result)):
        resp = await client.get("/api/webpush/subscriptions")
        assert resp.status_code == 200
        assert resp.json()["data"]["total_users"] == 1

@pytest.mark.asyncio
async def test_push_all(client):
    req = {
        "data": {
            "title": "Test Title",
            "content": "Test Content",
            "url": "https://example.com"
        }
    }
    mock_result = {"total": 5, "success": 4, "fail": 1}
    with patch("api.webpush.controller.push_to_all_webpush", AsyncMock(return_value=mock_result)):
        resp = await client.post("/api/webpush/push/all", json=req)
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 5

@pytest.mark.asyncio
async def test_push_user(client):
    req = {
        "user_id": MOCK_USER_ID,
        "data": {
            "title": "Test Title",
            "content": "Test Content",
            "url": "https://example.com"
        }
    }
    mock_result = {"total": 2, "success": 2, "fail": 0}
    with patch("api.webpush.controller.push_to_user_webpush", AsyncMock(return_value=mock_result)):
        resp = await client.post("/api/webpush/push/user", json=req)
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 2

@pytest.mark.asyncio
async def test_push_role(client):
    req = {
        "role": MOCK_ROLE,
        "data": {
            "title": "Test Title",
            "content": "Test Content",
            "url": "https://example.com"
        }
    }
    mock_result = {"total": 3, "success": 3, "fail": 0}
    with patch("api.webpush.controller.push_to_role_webpush", AsyncMock(return_value=mock_result)):
        resp = await client.post("/api/webpush/push/role", json=req)
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 3 