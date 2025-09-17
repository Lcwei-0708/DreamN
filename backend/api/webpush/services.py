import logging
from datetime import datetime
from sqlalchemy import select
from models import WebPushSubscription
from extensions.webpush import get_webpush
from extensions.keycloak import get_keycloak
from sqlalchemy.ext.asyncio import AsyncSession
from utils.custom_exception import ServerException, UserNotFoundException, WebPushSubscriptionNotFoundException
from .schema import WebPushSubscriptionResponse, WebPushSubscriptionInfo, UserWebPushInfo, WebPushSubscriptionsResponse, WebPushMessageData

keycloak = get_keycloak()
logger = logging.getLogger(__name__)


async def get_all_webpush_subscriptions(db: AsyncSession):
    result = await db.execute(select(WebPushSubscription))
    subscriptions = result.scalars().all()
    user_map = {}
    for subscription in subscriptions:
        info = WebPushSubscriptionInfo(
            id=subscription.id,
            endpoint=subscription.endpoint,
            keys=subscription.keys,
            is_active=subscription.is_active,
            user_agent=subscription.user_agent,
            created_at=subscription.created_at.isoformat(),
            updated_at=subscription.updated_at.isoformat()
        )
        if subscription.user_id not in user_map:
            user_map[subscription.user_id] = []
        user_map[subscription.user_id].append(info)
    users = [
        UserWebPushInfo(
            user_id=user_id,
            total_subscriptions=len(sub_list),
            subscriptions=sub_list
        )
        for user_id, sub_list in user_map.items()
    ]
    return WebPushSubscriptionsResponse(
        total_users=len(users),
        total_subscriptions=len(subscriptions),
        users=users
    )

async def subscribe_webpush(db: AsyncSession, token: str, endpoint: str, keys: dict, user_agent: str = None):
    try:
        user_id = await keycloak.get_user_id(token)
        if not user_id:
            raise UserNotFoundException("User not found")
        
        if not user_agent:
            user_agent = "Unknown"
        
        result = await db.execute(select(WebPushSubscription).filter_by(endpoint=endpoint))
        subscribe = result.scalars().first()
        
        if subscribe:
            if subscribe.user_id != user_id:
                subscribe.user_id = user_id
            subscribe.keys = keys
            subscribe.user_agent = user_agent
            subscribe.is_active = True
        else:
            subscribe = WebPushSubscription(
                user_id=user_id,
                endpoint=endpoint,
                keys=keys,
                user_agent=user_agent,
                is_active=True
            )
            db.add(subscribe)
        
        await db.commit()
        await db.refresh(subscribe)
        return WebPushSubscriptionResponse(
            id=subscribe.id,
            endpoint=subscribe.endpoint
        )
    except UserNotFoundException:
        raise
    except Exception as e:
        raise ServerException(f"Failed to subscribe webpush: {e}")

async def unsubscribe_webpush(db: AsyncSession, token: str, endpoint: str):
    try:
        user_id = await keycloak.get_user_id(token)
        logger.info(f"user_id: {user_id}")
        if not user_id:
            raise UserNotFoundException("User not found")
        
        result = await db.execute(select(WebPushSubscription).filter_by(endpoint=endpoint))
        subscribe = result.scalars().first()
        logger.info(f"subscribe: {subscribe}")
        if subscribe and subscribe.user_id == user_id:
            subscribe.is_active = False
            await db.flush()
            await db.commit()
            await db.refresh(subscribe)
            logger.info(f"after update: {subscribe.is_active}")
            return True
        else:
            raise WebPushSubscriptionNotFoundException("Subscription not found or not owned by user")
    except UserNotFoundException:
        raise
    except WebPushSubscriptionNotFoundException:
        raise
    except Exception as e:
        raise ServerException(f"Failed to unsubscribe webpush: {e}")

async def push_to_all_webpush(db: AsyncSession, data: WebPushMessageData):
    webpush = get_webpush()
    return await webpush.push_to_all(db, data)

async def push_to_user_webpush(db: AsyncSession, user_id: str, data: WebPushMessageData):
    webpush = get_webpush()
    return await webpush.push_to_user(db, user_id, data)

async def push_to_role_webpush(db: AsyncSession, role: str, data: WebPushMessageData, keycloak=None):
    webpush = get_webpush()
    return await webpush.push_to_role(db, role, data, keycloak)