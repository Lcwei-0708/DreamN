import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime
from utils.custom_exception import ServerException, InvalidPasswordException

@pytest.mark.asyncio
async def test_get_user_info_success(client):
    fake_token = "fake_token"
    fake_userinfo = {
        "sub": "user123",
        "preferred_username": "testuser",
        "given_name": "Test",
        "family_name": "User",
        "email": "testuser@example.com",
        "phone": "0912345678",
        "enabled": True,
        "realm_access": {"roles": ["user"]}
    }
    fake_roles = [{"name": "user"}]
    fake_last_login = datetime.fromisoformat("2024-06-29T12:00:00+08:00")

    with patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakOpenID.a_userinfo", new_callable=AsyncMock, return_value=fake_userinfo), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_roles), \
         patch("websocket.manager.ConnectionManager.get_user_last_ws_login", new_callable=AsyncMock, return_value=(True, fake_last_login)):

        response = await client.get(
            "/api/user/info",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == "user123"
        assert data["username"] == "testuser"
        assert data["roles"] == ["user"]
        assert data["lastLogin"] == fake_last_login.astimezone().isoformat()

@pytest.mark.asyncio
async def test_get_user_info_invalid_token(client):
    with patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value=None), \
         patch("extensions.keycloak.KeycloakOpenID.a_userinfo", new_callable=AsyncMock, side_effect=ServerException("Token authentication failed")):
        response = await client.get(
            "/api/user/info",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_update_user_info_success(client):
    fake_token = "fake_token"
    fake_userinfo = {
        "sub": "user123",
        "preferred_username": "testuser",
        "given_name": "Test",
        "family_name": "User",
        "email": "testuser@example.com",
        "phone": "0912345678",
        "enabled": True
    }
    fake_current_user = {"id": "user123", "email": "testuser@example.com"}
    
    with patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakOpenID.a_userinfo", new_callable=AsyncMock, return_value=fake_userinfo), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_user", new_callable=AsyncMock, return_value=fake_current_user), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_users", new_callable=AsyncMock, return_value=[]), \
         patch("extensions.keycloak.KeycloakAdmin.a_update_user", new_callable=AsyncMock, return_value=None):
        response = await client.put(
            "/api/user/update",
            headers={"Authorization": f"Bearer {fake_token}"},
            json={
                "firstName": "NewName",
                "lastName": "User",
                "email": "testuser@example.com",
                "phone": "0912345678"
            }
        )
        assert response.status_code == 200
        assert response.json()["message"] == "User info updated successfully"

@pytest.mark.asyncio
async def test_change_password_success(client):
    fake_token = "fake_token"
    with patch("extensions.keycloak.KeycloakExtension.get_user_id", return_value="user123"), \
         patch("extensions.keycloak.KeycloakOpenID.a_userinfo", return_value={"sub": "user123", "preferred_username": "testuser"}), \
         patch("extensions.keycloak.KeycloakOpenID.a_token", new_callable=AsyncMock, return_value={"access_token": "abc"}), \
         patch("extensions.keycloak.KeycloakAdmin.a_set_user_password", new_callable=AsyncMock, return_value=None), \
         patch("extensions.keycloak.KeycloakAdmin.a_user_logout", new_callable=AsyncMock, return_value=None):
        response = await client.put(
            "/api/user/change-password",
            headers={"Authorization": f"Bearer {fake_token}"},
            json={"old_password": "oldpw123", "new_password": "newStrongPassword123"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"

@pytest.mark.asyncio
async def test_change_password_invalid_token(client):
    with patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value=None), \
         patch("extensions.keycloak.KeycloakOpenID.a_userinfo", new_callable=AsyncMock, side_effect=InvalidPasswordException("Password change failed")):
        response = await client.put(
            "/api/user/change-password",
            headers={"Authorization": "Bearer invalid_token"},
            json={"old_password": "oldpw123", "new_password": "newStrongPassword123"}
        )
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_change_password_wrong_old_password(client):
    fake_token = "fake_token"
    
    def mock_token_error(*args, **kwargs):
        raise Exception("Invalid password")
    
    with patch("extensions.keycloak.KeycloakExtension.get_user_id", return_value="user123"), \
         patch("extensions.keycloak.KeycloakOpenID.a_userinfo", return_value={"sub": "user123", "preferred_username": "testuser"}), \
         patch("extensions.keycloak.KeycloakOpenID.a_token", new_callable=AsyncMock, side_effect=mock_token_error):
        response = await client.put(
            "/api/user/change-password",
            headers={"Authorization": f"Bearer {fake_token}"},
            json={"old_password": "wrongpw", "new_password": "newStrongPassword123"}
        )
        assert response.status_code == 401