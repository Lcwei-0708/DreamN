import pytest

pytestmark = pytest.mark.asyncio

@pytest.fixture
def anyio_backend():
    return 'asyncio'

async def test_broadcast_api(client):
    # Test broadcast API
    payload = {"type": "test", "data": {"msg": "hello all"}}
    resp = await client.post("/api/websocket/broadcast", json=payload)
    assert resp.status_code == 200
    assert resp.json()["code"] == 200

async def test_push_message_to_user_api(client):
    # Test pushing message to specific user
    payload = {"user_id": "user_001", "type": "notify", "data": {"msg": "hi user"}}
    resp = await client.post("/api/websocket/push", json=payload)
    # Expected 404 since mock redis has no user data
    assert resp.status_code == 404

async def test_push_message_to_role_api(client):
    # Test pushing message to specific role
    payload = {"role": "admin", "type": "notify", "data": {"msg": "hi admin"}}
    resp = await client.post("/api/websocket/push-by-role", json=payload)
    # Expected 404 due to mock keycloak and redis
    assert resp.status_code == 404

async def test_get_online_users(client):
    resp = await client.get("/api/websocket/online-users")
    assert resp.status_code == 200
    data = resp.json()
    assert "code" in data and "data" in data
    assert "total_users" in data["data"]
    # Mock redis returns empty list, so total users should be 0
    assert data["data"]["total_users"] == 0 