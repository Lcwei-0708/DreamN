import json
import logging
from urllib.parse import urlparse
from typing import Dict, Any, Optional

from core.config import settings
from pywebpush import webpush, WebPushException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import WebPushSubscription
from extensions.keycloak import get_keycloak
from utils.custom_exception import ServerException, UserNotFoundException, RoleNotFoundException

logger = logging.getLogger("webpush_notification")

# Constants definition
class WebPushConstants:
    WNS_DOMAIN = 'notify.windows.com'
    WNS_TTL = 0
    WNS_CACHE_POLICY_HEADER = 'x-wns-cache-policy'
    CACHE_POLICY_NO_CACHE = 'no-cache'
    CACHE_POLICY_CACHE = 'cache'

class WebPushExtension:
    """Web push notification service"""
    
    def __init__(self):
        """Initialize web push service"""
        self.vapid_private_key = settings.VAPID_PRIVATE_KEY
        self.vapid_public_key = settings.VAPID_PUBLIC_KEY
        self.vapid_email = settings.VAPID_EMAIL

    def is_wns_endpoint(self, endpoint: str) -> bool:
        """
        Check if the endpoint is a Windows Notification Service (WNS) endpoint
        
        Args:
            endpoint: Push endpoint URL
            
        Returns:
            bool: True if it's a WNS endpoint
        """
        try:
            parsed = urlparse(endpoint)
            return WebPushConstants.WNS_DOMAIN in parsed.netloc.lower()
        except Exception as e:
            logger.warning(f"Failed to parse endpoint URL: {endpoint}, error: {e}")
            return False

    def _build_vapid_claims(self, endpoint: str) -> Dict[str, str]:
        """
        Build VAPID claims
        
        Args:
            endpoint: Push endpoint URL
            
        Returns:
            Dict[str, str]: VAPID claims dictionary
        """
        parsed = urlparse(endpoint)
        aud = f"{parsed.scheme}://{parsed.netloc}"
        
        return {
            "sub": f"mailto:{self.vapid_email}",
            "aud": aud
        }

    def _send_wns_push(self, subscription_info: Dict[str, Any], message: str, vapid_claims: Dict[str, str]) -> bool:
        """
        Send WNS push notification
        
        Args:
            subscription_info: Push subscription information
            message: Message to send
            vapid_claims: VAPID claims
            
        Returns:
            bool: True if sent successfully
        """
        logger.info("Detected WNS endpoint, using WNS-specific headers")
        logger.info(f"WNS endpoint forcing TTL to {WebPushConstants.WNS_TTL}")
        
        headers = {
            WebPushConstants.WNS_CACHE_POLICY_HEADER: WebPushConstants.CACHE_POLICY_NO_CACHE
        }
        
        webpush(
            subscription_info=subscription_info,
            data=message,
            vapid_private_key=self.vapid_private_key,
            vapid_claims=vapid_claims,
            headers=headers
        )
        return True

    def _send_standard_push(self, subscription_info: Dict[str, Any], message: str, vapid_claims: Dict[str, str]) -> bool:
        """
        Send standard push notification
        
        Args:
            subscription_info: Push subscription information
            message: Message to send
            vapid_claims: VAPID claims
            
        Returns:
            bool: True if sent successfully
        """
        logger.info("Using standard web push")
        
        webpush(
            subscription_info,
            message,
            vapid_private_key=self.vapid_private_key,
            vapid_claims=vapid_claims
        )
        return True

    def send_push(self, subscription_info: Dict[str, Any], message: str, ttl: int = 0) -> bool:
        """
        Send push notification with automatic endpoint type detection
        
        Args:
            subscription_info: Push subscription information
            message: Message to send
            ttl: Time to live in seconds, default is 0
            
        Returns:
            bool: True if sent successfully, False if failed
        """
        try:
            endpoint = subscription_info["endpoint"]
            vapid_claims = self._build_vapid_claims(endpoint)
            
            logger.info(f"Preparing to send push notification to: {endpoint}")
            logger.info(f"VAPID claims: {vapid_claims}")

            # Choose sending method based on endpoint type
            if self.is_wns_endpoint(endpoint):
                return self._send_wns_push(subscription_info, message, vapid_claims)
            else:
                return self._send_standard_push(subscription_info, message, vapid_claims)
                
        except WebPushException as ex:
            self._handle_webpush_exception(ex)
            return False
        except Exception as e:
            logger.error(f"Unexpected error occurred while sending push notification: {e}")
            return False

    def _handle_webpush_exception(self, ex: WebPushException) -> None:
        """
        Handle WebPush exception
        
        Args:
            ex: WebPushException object
        """
        logger.error(f"Web push exception: {ex}")
        
        if hasattr(ex, 'response') and ex.response:
            logger.error(f"Response status code: {ex.response.status_code}")
            logger.error(f"Response content: {ex.response.text}")

    async def push_to_all(self, db: AsyncSession, data):
        try:
            result = await db.execute(select(WebPushSubscription).filter_by(is_active=True))
            subscriptions = result.scalars().all()
        except Exception as e:
            raise ServerException(f"Select WebPushSubscription failed: {e}")
        success, fail = 0, 0
        for sub in subscriptions:
            try:
                sub_info = {
                    "endpoint": sub.endpoint,
                    "keys": sub.keys
                }
                if self.send_push(sub_info, json.dumps(data.dict())):
                    success += 1
                else:
                    sub.is_active = False
                    await db.commit()
                    fail += 1
            except WebPushException as e:
                if hasattr(e, 'response') and e.response and e.response.status_code in (404, 410, 403):
                    sub.is_active = False
                    await db.commit()
                fail += 1
                logger.error(f"Web push send error: {e}")
            except Exception as e:
                fail += 1
                raise ServerException(f"Web push send error: {e}")
        total = success + fail
        return {"total": total, "success": success, "fail": fail}

    async def push_to_user(self, db: AsyncSession, user_id: str, data):
        try:
            result = await db.execute(select(WebPushSubscription).filter_by(user_id=user_id, is_active=True))
            subscriptions = result.scalars().all()
        except Exception as e:
            raise ServerException(f"Select WebPushSubscription failed: {e}")
        if not subscriptions:
            raise UserNotFoundException(f"User {user_id} has no subscriptions")
        success, fail = 0, 0
        for sub in subscriptions:
            try:
                sub_info = {
                    "endpoint": sub.endpoint,
                    "keys": sub.keys
                }
                if self.send_push(sub_info, json.dumps(data.dict())):
                    success += 1
                else:
                    sub.is_active = False
                    await db.commit()
                    fail += 1
            except WebPushException as e:
                if hasattr(e, 'response') and e.response and e.response.status_code in (404, 410, 403):
                    sub.is_active = False
                    await db.commit()
                logger.error(f"Web push send error: {e}")
                fail += 1
            except Exception as e:
                fail += 1
                logger.error(f"Web push send error: {e}")
        total = success + fail
        return {"total": total, "success": success, "fail": fail}

    async def push_to_role(self, db: AsyncSession, role: str, data, keycloak=None):
        if keycloak is None:
            keycloak = get_keycloak()
        try:
            users = await keycloak.keycloak_admin.a_get_realm_role_members(role, {})
        except Exception as e:
            raise RoleNotFoundException(f"Select Keycloak users failed: {e}")
        user_ids = [user['id'] for user in users]
        if not user_ids:
            raise UserNotFoundException(f"Role {role} has no users")
        success, fail = 0, 0
        for user_id in user_ids:
            try:
                result = await db.execute(select(WebPushSubscription).filter_by(user_id=user_id, is_active=True))
                subscriptions = result.scalars().all()
            except Exception as e:
                logger.error(f"WebPushDBException: Select WebPushSubscription failed: {e}")
                continue
            for sub in subscriptions:
                try:
                    sub_info = {
                        "endpoint": sub.endpoint,
                        "keys": sub.keys
                    }
                    if self.send_push(sub_info, json.dumps(data.dict())):
                        success += 1
                    else:
                        sub.is_active = False
                        await db.commit()
                        fail += 1
                except WebPushException as e:
                    if hasattr(e, 'response') and e.response and e.response.status_code in (404, 410, 403):
                        sub.is_active = False
                        await db.commit()
                    fail += 1
                    logger.error(f"Web push send error: {e}")
                except Exception as e:
                    fail += 1
                    raise ServerException(f"Web push send error: {e}")
        total = success + fail
        return {"total": total, "success": success, "fail": fail}

# Global instance management
_WEB_PUSH_SERVICE: Optional[WebPushExtension] = None

def get_webpush() -> WebPushExtension:
    """
    Get web push service instance (singleton pattern)
    
    Returns:
        WebPushExtension: Web push service instance
    """
    global _WEB_PUSH_SERVICE
    if _WEB_PUSH_SERVICE is None:
        _WEB_PUSH_SERVICE = WebPushExtension()
    return _WEB_PUSH_SERVICE

def add_webpush(app) -> None:
    """
    Add web push service to application state
    
    Args:
        app: FastAPI application instance
    """
    app.state.webpush = get_webpush()