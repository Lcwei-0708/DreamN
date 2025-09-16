from websocket.manager import get_manager
from extensions.keycloak import get_keycloak
from sqlalchemy.ext.asyncio import AsyncSession
from utils.custom_exception import (
    ServerException,
    InvalidPasswordException,
    EmailAlreadyExistsException,
)

ws_manager = get_manager()
keycloak = get_keycloak()
keycloak_openid = keycloak.keycloak_openid
keycloak_admin = keycloak.keycloak_admin

async def get_current_user_info(token: str, db: AsyncSession):
    try:
        userinfo = await keycloak_openid.a_userinfo(token)
        user_id = userinfo.get("sub")
        roles = userinfo.get("realm_access", {}).get("roles", [])
        custom_roles = [r for r in roles if keycloak.is_custom_role(r)]
            
        # Get last login status and time
        _, last_login_dt = await ws_manager.get_user_last_ws_login(user_id, db)
        if last_login_dt:
            last_login = last_login_dt.astimezone().isoformat()
        else:
            last_login = None
        
        user_data = {
            "id": user_id,
            "username": userinfo.get("preferred_username"),
            "firstName": userinfo.get("given_name", ""),
            "lastName": userinfo.get("family_name", ""),
            "email": userinfo.get("email", ""),
            "phone": userinfo.get("phone", ""),
            "enabled": userinfo.get("enabled", True),
            "roles": custom_roles,
            "lastLogin": last_login
        }
        return user_data
    except Exception as e:
        raise ServerException(f"Token authentication failed: {str(e)}")

async def update_current_user_info(token: str, update_data: dict):
    user_id = await keycloak.get_user_id(token)
    try:
        data = update_data.copy()
        if "email" in data:
            current_user = await keycloak_admin.a_get_user(user_id)
            current_email = current_user.get("email")
            new_email = data["email"]
            if new_email and new_email != current_email:
                users_with_email = await keycloak_admin.a_get_users({"email": new_email})
                if users_with_email and any(u["id"] != user_id for u in users_with_email):
                    raise EmailAlreadyExistsException(f"email: {new_email}")
        if "phone" in data:
            phone = data.pop("phone")
            data.setdefault("attributes", {})
            data["attributes"]["phone"] = [phone] if phone is not None else []

        await keycloak_admin.a_update_user(user_id, data)
        return True
    except EmailAlreadyExistsException:
        raise
    except Exception as e:
        raise ServerException(f"Update failed: {str(e)}")

async def change_current_user_password(token: str, old_password: str, new_password: str, logout_all_devices: bool = True):
    user_id = await keycloak.get_user_id(token)
    try:
        userinfo = await keycloak_openid.a_userinfo(token)
        username = userinfo.get("preferred_username")
        
        # Verify old password
        try:
            await keycloak_openid.a_token(username, old_password)
        except Exception as e:
            raise InvalidPasswordException("Old password is incorrect")
        
        # Change new password
        await keycloak_admin.a_set_user_password(user_id, new_password, temporary=False)
        
        # Logout all devices
        if logout_all_devices:
            try:
                await keycloak_admin.a_user_logout(user_id)
            except Exception as e:
                raise ServerException(f"Failed to logout all devices: {str(e)}")
        
        return True
    except InvalidPasswordException:
        raise
    except Exception as e:
        raise ServerException(f"Password change failed: {str(e)}")