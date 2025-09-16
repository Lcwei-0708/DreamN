import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_get_users_success(client):
    fake_token = "fake_token"
    
    # Mock Keycloak data
    fake_users = [
        {
            "id": "user123",
            "username": "testuser1",
            "firstName": "Test",
            "lastName": "User1",
            "email": "test1@example.com",
            "enabled": True,
            "attributes": {
                "phone": ["0912345678"],
                "roles": ["admin"]
            }
        },
        {
            "id": "user456", 
            "username": "testuser2",
            "firstName": "Test",
            "lastName": "User2", 
            "email": "test2@example.com",
            "enabled": True,
            "attributes": {
                "phone": ["0987654321"],
                "roles": ["admin"]
            }
        }
    ]
    
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}
    fake_last_login = datetime.fromisoformat("2024-06-29T12:00:00+08:00")

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_users", new_callable=AsyncMock, return_value=fake_users), \
         patch("extensions.keycloak.KeycloakExtension.is_custom_role", new_callable=AsyncMock, return_value=True), \
         patch("websocket.manager.ConnectionManager.get_user_last_ws_login", new_callable=AsyncMock, return_value=(True, fake_last_login)):
        response = await client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["total"] == 2

@pytest.mark.asyncio
async def test_get_users_with_filters(client):
    fake_token = "fake_token"
    fake_users = []
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}
    fake_last_login = datetime.fromisoformat("2024-06-29T12:00:00+08:00")

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_users", new_callable=AsyncMock, return_value=fake_users), \
         patch("extensions.keycloak.KeycloakExtension.is_custom_role", new_callable=AsyncMock, return_value=True), \
         patch("websocket.manager.ConnectionManager.get_user_last_ws_login", new_callable=AsyncMock, return_value=(False, fake_last_login)):
        response = await client.get(
            "/api/admin/users?name=test&status=true&role=admin&page=1&per_page=5&sort_by=username&desc=false",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        assert response.json()["code"] == 200

@pytest.mark.asyncio
async def test_create_user_success(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_create_user", new_callable=AsyncMock, return_value="new-user-123"):
        payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "firstName": "New",
            "lastName": "User",
            "phone": "0987654321",
            "password": "strongpassword123",
            "enabled": True,
            "roles": []
        }
        response = await client.post(
            "/api/admin/users", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["user_id"] == "new-user-123"

@pytest.mark.asyncio
async def test_create_user_email_exists(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    def mock_create_user_error(*args, **kwargs):
        raise Exception("User exists with same email")

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_create_user", side_effect=mock_create_user_error):
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "User",
            "password": "password123",
            "enabled": True,
            "roles": []  # 加入 roles 欄位
        }
        response = await client.post(
            "/api/admin/users", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 409

@pytest.mark.asyncio
async def test_update_user_success(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}
    fake_current_user = {"id": "user123", "email": "old@example.com"}

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_user", new_callable=AsyncMock, return_value=fake_current_user), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_users", new_callable=AsyncMock, return_value=[]), \
         patch("extensions.keycloak.KeycloakAdmin.a_update_user", new_callable=AsyncMock, return_value=None):
        payload = {
            "email": "updated@example.com",
            "firstName": "Updated",
            "lastName": "User",
            "phone": "0911111111",
            "enabled": False
        }
        response = await client.put(
            "/api/admin/users/user123", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "User updated successfully"

@pytest.mark.asyncio
async def test_update_user_not_found(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    def mock_get_user_error(*args, **kwargs):
        raise Exception("404: User not found")

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_user", side_effect=mock_get_user_error), \
         patch("extensions.keycloak.KeycloakAdmin.a_update_user", side_effect=mock_get_user_error):
        payload = {"firstName": "Updated"}
        response = await client.put(
            "/api/admin/users/nonexistent", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_users_success(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_delete_user", return_value=None):
        payload = {"user_ids": ["user123"]}
        response = await client.request(
            "DELETE",
            "/api/admin/users",
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "All users deleted successfully"

@pytest.mark.asyncio
async def test_delete_users_partial_success(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    def mock_delete_user_side_effect(user_id):
        if user_id == "user123":
            return None
        else:
            raise Exception("404: User not found")

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_delete_user", side_effect=mock_delete_user_side_effect):
        payload = {"user_ids": ["user123", "nonexistent"]}
        response = await client.request(
            "DELETE",
            "/api/admin/users",
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 207
        data = response.json()
        assert data["code"] == 207
        assert data["message"] == "Delete users partial success"
        assert data["data"]["total_requested"] == 2
        assert data["data"]["deleted_count"] == 1
        assert data["data"]["failed_count"] == 1
        assert len(data["data"]["results"]) == 2
        
        success_results = [r for r in data["data"]["results"] if r["status"] == "success"]
        failed_results = [r for r in data["data"]["results"] if r["status"] == "not_found"]
        assert len(success_results) == 1
        assert len(failed_results) == 1
        assert success_results[0]["id"] == "user123"
        assert failed_results[0]["id"] == "nonexistent"

@pytest.mark.asyncio
async def test_delete_users_all_failed(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_delete_user", side_effect=Exception("User not found")):
        payload = {"user_ids": ["nonexistent1", "nonexistent2"]}
        response = await client.request(
            "DELETE",
            "/api/admin/users",
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 400
        assert data["message"] == "All users failed to delete"
        assert data["data"]["results"]
        assert len(data["data"]["results"]) == 2

@pytest.mark.asyncio
async def test_reset_password_success(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_set_user_password", return_value=None), \
         patch("extensions.keycloak.KeycloakAdmin.a_user_logout", return_value=None):
        payload = {"password": "newpassword123"}
        response = await client.post(
            "/api/admin/users/user123/reset-password", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password reset successfully"

@pytest.mark.asyncio
async def test_reset_password_user_not_found(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    def mock_reset_password_error(*args, **kwargs):
        raise Exception("404: User not found")

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_set_user_password", side_effect=mock_reset_password_error):
        payload = {"password": "newpassword123"}
        response = await client.post(
            "/api/admin/users/nonexistent/reset-password", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_roles_success(client):
    fake_token = "fake_token"
    fake_realm_roles = [
        {"id": "role123", "name": "admin", "description": "Administrator role"},
        {"id": "role456", "name": "manager", "description": "Manager role"}
    ]
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}
    fake_full_role_admin = {"attributes": {"permissions": ["read", "write"]}}
    fake_full_role_manager = {"attributes": None}

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role") as mock_get_role, \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles", return_value=fake_realm_roles), \
         patch("extensions.keycloak.KeycloakExtension.is_custom_role", new_callable=AsyncMock, return_value=True):
        
        def mock_role_response(role_name):
            if role_name == "admin":
                return fake_role_info if role_name == "admin" else fake_full_role_admin
            elif role_name == "manager":
                return fake_role_info if role_name == "admin" else fake_full_role_manager
            return fake_role_info
        
        mock_get_role.side_effect = mock_role_response
        
        response = await client.get(
            "/api/admin/roles",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["roles"]) == 2

@pytest.mark.asyncio
async def test_create_role_success(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_create_realm_role", return_value=None):
        payload = {
            "name": "newrole",
            "description": "A new role for testing"
        }
        response = await client.post(
            "/api/admin/roles", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["role_name"] == "newrole"

@pytest.mark.asyncio
async def test_create_role_already_exists(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    def mock_create_role_error(*args, **kwargs):
        raise Exception("409: Role exists")

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_create_realm_role", side_effect=mock_create_role_error):
        payload = {
            "name": "admin",
            "description": "Duplicate role"
        }
        response = await client.post(
            "/api/admin/roles", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 409

@pytest.mark.asyncio
async def test_update_role_success(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}
    fake_existing_role = {"name": "testrole", "description": "Old description"}

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info if fake_role_info else fake_existing_role), \
         patch("extensions.keycloak.KeycloakAdmin.a_update_realm_role", return_value=None):
        payload = {"description": "Updated description"}
        response = await client.put(
            "/api/admin/roles/testrole", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Role updated successfully"

@pytest.mark.asyncio
async def test_update_role_not_found(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    def mock_get_role_error(*args, **kwargs):
        if args[0] == "admin":  # Permission check
            return fake_role_info
        raise Exception("404: Role not found")

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", side_effect=mock_get_role_error), \
         patch("extensions.keycloak.KeycloakAdmin.a_update_realm_role", side_effect=mock_get_role_error):
        payload = {"description": "Updated description"}
        response = await client.put(
            "/api/admin/roles/nonexistent", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_role_attributes_success(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}
    fake_existing_role = {"name": "testrole", "attributes": {"old": ["value"]}}

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info if fake_role_info else fake_existing_role), \
         patch("extensions.keycloak.KeycloakAdmin.a_update_realm_role", return_value=None):
        payload = {
            "attributes": {
                "permissions": True,
                "department": True
            }
        }
        response = await client.put(
            "/api/admin/roles/testrole/attributes", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Role attributes updated successfully"

@pytest.mark.asyncio
async def test_update_role_attributes_not_found(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    def mock_get_role_error(*args, **kwargs):
        if args[0] == "admin":  # Permission check
            return fake_role_info
        raise Exception("404: Role not found")

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", side_effect=mock_get_role_error), \
         patch("extensions.keycloak.KeycloakAdmin.a_update_realm_role", side_effect=mock_get_role_error):
        payload = {"attributes": {"key": True}}
        response = await client.put(
            "/api/admin/roles/nonexistent/attributes", 
            json=payload,
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_role_success(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", new_callable=AsyncMock, return_value=fake_role_info), \
         patch("extensions.keycloak.KeycloakAdmin.a_delete_realm_role", return_value=None):
        response = await client.delete(
            "/api/admin/roles/testrole",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Role deleted successfully"

@pytest.mark.asyncio
async def test_delete_role_not_found(client):
    fake_token = "fake_token"
    fake_user_roles = [{"name": "admin"}]
    fake_role_info = {"attributes": {"admin": ["true"]}}

    def mock_delete_role_error(*args, **kwargs):
        if args[0] == "admin":  # Permission check for get_realm_role  
            return fake_role_info
        raise Exception("404: Role not found")

    with patch("extensions.keycloak.KeycloakExtension.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("extensions.keycloak.KeycloakExtension.get_user_id", new_callable=AsyncMock, return_value="user123"), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_roles_of_user", new_callable=AsyncMock, return_value=fake_user_roles), \
         patch("extensions.keycloak.KeycloakAdmin.a_get_realm_role", side_effect=mock_delete_role_error), \
         patch("extensions.keycloak.KeycloakAdmin.a_delete_realm_role", side_effect=mock_delete_role_error):
        response = await client.delete(
            "/api/admin/roles/nonexistent",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 404