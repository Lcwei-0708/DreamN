import re
import logging
from typing import Optional
from functools import wraps
from core.config import settings
from fastapi import HTTPException
from keycloak import KeycloakAdmin, KeycloakOpenID

class KeycloakExtension:
    def __init__(self):
        # keycloak config
        self.server_url = settings.KEYCLOAK_SERVER_URL
        self.realm_name = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_ADMIN_CLIENT
        self.client_secret_key = settings.KEYCLOAK_ADMIN_CLIENT_SECRET
        self.verify = settings.KEYCLOAK_VERIFY
        # keycloak admin
        self.keycloak_admin = KeycloakAdmin(
            server_url=self.server_url,
            realm_name=self.realm_name,
            client_id=self.client_id,
            client_secret_key=self.client_secret_key,
            verify=self.verify
        )
        # keycloak openid
        self.keycloak_openid = KeycloakOpenID(
            server_url=self.server_url,
            realm_name=self.realm_name,
            client_id=self.client_id,
            client_secret_key=self.client_secret_key,
            verify=self.verify
        )

    def require_permission(self, module_name: str):
        logger = logging.getLogger("keycloak_permission")
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                token = kwargs.get("token")
                if not token:
                    raise HTTPException(status_code=401)
                user_id = await self.get_user_id(token)
                if not user_id:
                    raise HTTPException(status_code=401)

                user_roles = await self.keycloak_admin.a_get_realm_roles_of_user(user_id)
                logger.info(f"{user_id}: {user_roles}")

                for role in user_roles:
                    role_name = role["name"]
                    role_info = await self.keycloak_admin.a_get_realm_role(role_name)
                    attributes = role_info.get("attributes", {})
                    if attributes.get(module_name, False):
                        return await func(*args, **kwargs)

                logger.info(f"Permission denied for user {user_id} on module {module_name}. Checked roles: {[r['name'] for r in user_roles]}")
                raise HTTPException(status_code=403)
            return wrapper
        return decorator
    
    async def verify_token(self, token: str):
        logger = logging.getLogger("keycloak_verify")
        try:
            userinfo = await self.keycloak_openid.a_userinfo(token)
            if userinfo:
                return True
            return False
        except Exception as e:
            logger.error(f"verify token error: {e}")
            return False

    async def get_user_id(self, token: str):
        try:
            userinfo = await self.keycloak_openid.a_userinfo(token)
            if userinfo:
                return userinfo.get("sub")
            return None
        except Exception:
            return None
    
    def is_custom_role(self, role_name):
        default_roles = [
            "two-shoulder", "offline_access", "uma_authorization"
        ]
        if role_name.startswith("default-roles-"):
            return False
        if role_name in default_roles:
            return False
        return True

    def parse_attributes(self, attributes: dict) -> dict:
        """
        Convert {"admin": ["true"], "other": ["false"]} to {"admin": True, "other": False}
        """
        result = {}
        for k, v in (attributes or {}).items():
            if isinstance(v, list) and v:
                val = v[0]
            else:
                val = v
            if isinstance(val, str) and val.lower() in ("true", "false"):
                result[k] = val.lower() == "true"
            else:
                result[k] = val
        return result

    def format_attributes(self, attributes: dict) -> dict:
        """
        Convert {"admin": True, "other": False} to {"admin": ["true"], "other": ["false"]}
        """
        result = {}
        for k, v in (attributes or {}).items():
            if isinstance(v, bool):
                result[k] = [str(v).lower()]
            else:
                result[k] = [str(v)]
        return result

    def extract_status_code_from_error(self, error_str: str) -> Optional[int]:
        """Extract HTTP status code from Keycloak error message"""
        match = re.search(r'(\d{3}):', error_str)
        if match:
            return int(match.group(1))
        return None

    def is_keycloak_404_error(self, error_str: str) -> bool:
        """Check if the error is a Keycloak 404 error"""
        status_code = self.extract_status_code_from_error(error_str)
        return status_code == 404

    def is_keycloak_409_error(self, error_str: str) -> bool:
        """Check if the error is a Keycloak 409 error (conflict)"""
        status_code = self.extract_status_code_from_error(error_str)
        return status_code == 409

_KEYCLOAK_EXTENSION: Optional[KeycloakExtension] = None

def get_keycloak() -> KeycloakExtension:
    global _KEYCLOAK_EXTENSION
    if _KEYCLOAK_EXTENSION is None:
        _KEYCLOAK_EXTENSION = KeycloakExtension()
    return _KEYCLOAK_EXTENSION

def add_keycloak(app):
    """
    Register keycloak to app.state
    """
    keycloak_ext = get_keycloak()
    app.state.keycloak = keycloak_ext.keycloak_admin