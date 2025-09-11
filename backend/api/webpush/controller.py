from core.dependencies import get_db
from core.security import verify_token
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Request
from utils.response import APIResponse, parse_responses, common_responses
from .services import ( 
    subscribe_webpush, 
    unsubscribe_webpush, 
    get_all_webpush_subscriptions, 
    push_to_all_webpush, 
    push_to_user_webpush, 
    push_to_role_webpush
)
from utils.custom_exception import (
    UserNotFoundException, 
    WebPushSubscriptionNotFoundException, 
    ServerException, 
    RoleNotFoundException
)
from .schema import (
    WebPushSubscriptionRequest, 
    WebPushUnsubscribeRequest, 
    WebPushSubscriptionResponse, 
    WebPushSubscriptionsResponse, 
    WebPushSendRequest,
    WebPushUserSendRequest,
    WebPushRoleSendRequest,
    WebPushSendResult,
    webpush_subscriptions_response_example,
    webpush_subscription_request_example
)

router = APIRouter(tags=["webpush"])

@router.get(
    "/subscriptions",
    response_model=APIResponse[WebPushSubscriptionsResponse],
    response_model_exclude_none=True,
    summary="Get all WebPush subscriptions (grouped by user)",
    responses=parse_responses({
        200: ("Get all subscriptions successfully", WebPushSubscriptionsResponse, webpush_subscriptions_response_example),
        404: ("Subscription not found", None)
    }, default=common_responses)
)
async def webpush_subscriptions_list(
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await get_all_webpush_subscriptions(db)
        return APIResponse(code=200, message="List all subscriptions successfully", data=result)
    except WebPushSubscriptionNotFoundException:
        raise HTTPException(status_code=404, detail="Subscription not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/subscribe",
    response_model=APIResponse[WebPushSubscriptionResponse],
    response_model_exclude_none=True,
    summary="Subscribe to WebPush",
    responses=parse_responses({
        200: ("Subscribe successfully", WebPushSubscriptionResponse),
        404: ("User not found", None)
    }, default=common_responses)
)
async def subscribe(
    request: Request,
    req: WebPushSubscriptionRequest = webpush_subscription_request_example,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verify_token)
):
    try:
        user_agent = req.user_agent or request.headers.get("user-agent", "Unknown")
        
        subscribe_info = await subscribe_webpush(
            db, 
            token, 
            req.endpoint, 
            req.keys, 
            user_agent
        )
        return APIResponse(
            code=200,
            message="Subscribed successfully",
            data=subscribe_info
        )
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/unsubscribe",
    response_model=APIResponse[None],
    response_model_exclude_none=True,
    summary="Unsubscribe from WebPush",
    responses=parse_responses({
        200: ("Unsubscribe successfully", None),
        404: ("Subscription not found / User not found", None)
    }, default=common_responses)
)
async def unsubscribe(
    req: WebPushUnsubscribeRequest,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verify_token)
):
    try:
        await unsubscribe_webpush(db, token, req.endpoint)
        return APIResponse(code=200, message="Unsubscribed successfully")
    except WebPushSubscriptionNotFoundException:
        raise HTTPException(status_code=404, detail="Subscription not found")
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/push/all",
    response_model=APIResponse[WebPushSendResult],
    response_model_exclude_none=True,
    summary="push to all endpoint",
    responses=parse_responses({
        200: ("Push to all successfully", WebPushSendResult)
    }, default=common_responses)
)
async def push_all(
    req: WebPushSendRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await push_to_all_webpush(db, req.data)
        return APIResponse(code=200, message="Push to all successfully", data=result)
    except ServerException:
        raise HTTPException(status_code=500)

@router.post(
    "/push/user",
    response_model=APIResponse[WebPushSendResult],
    response_model_exclude_none=True,
    summary="push to user endpoint",
    responses=parse_responses({
        200: ("Push to user successfully", WebPushSendResult),
        404: ("User not found", None)
    }, default=common_responses)
)
async def push_user(
    req: WebPushUserSendRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await push_to_user_webpush(db, req.user_id, req.data)
        return APIResponse(code=200, message="Push to user successfully", data=result)
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except ServerException:
        raise HTTPException(status_code=500)

@router.post(
    "/push/role",
    response_model=APIResponse[WebPushSendResult],
    response_model_exclude_none=True,
    summary="push to role endpoint",
    responses=parse_responses({
        200: ("Push to role successfully", WebPushSendResult),
        404: ("Role not found / User not found", None)
    }, default=common_responses)
)
async def push_role(
    req: WebPushRoleSendRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await push_to_role_webpush(db, req.role, req.data)
        return APIResponse(code=200, message="Push to role successfully", data=result)
    except RoleNotFoundException:
        raise HTTPException(status_code=404, detail="Role not found")
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except ServerException:
        raise HTTPException(status_code=500)