from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from websocket.manager import get_manager, ConnectionManager
from utils.response import APIResponse, parse_responses, common_responses
from utils.custom_exception import UserNotFoundException, RoleNotFoundException
from .services import fetch_online_users, push_message_to_user, push_message_to_role, broadcast_message
from .schema import OnlineUsersResponse, BroadcastRequest, UserPushRequest, RolePushRequest, online_users_response_example

router = APIRouter(tags=["websocket"])

REDIS_ONLINE_USERS_KEY = "ws:online_users"

@router.get(
    "/online-users",
    response_model=APIResponse[OnlineUsersResponse],
    response_model_exclude_unset=True,
    summary="Get all online users",
    responses=parse_responses({
        200: (
            "Get online users successfully",
            OnlineUsersResponse,
            online_users_response_example
        ),
    }, default=common_responses)
)
async def get_online_users():
    try:
        data = await fetch_online_users()
        return APIResponse(code=200, message="Get online users successfully", data=data)
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/broadcast",
    response_model=APIResponse[None],
    response_model_exclude_unset=True,
    summary="Broadcast message to all online users",
    responses=parse_responses({
        200: ("Message broadcasted successfully", None)
    }, default=common_responses)
)
async def broadcast_message_api(
    payload: BroadcastRequest,
    ws_manager: Annotated[ConnectionManager, Depends(get_manager)]
):
    try:
        await broadcast_message(payload.type, payload.data, ws_manager)
        return APIResponse(code=200, message="Message broadcasted successfully")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/push",
    response_model=APIResponse[None],
    response_model_exclude_unset=True,
    summary="Push message to all connections of a specific user",
    responses=parse_responses({
        200: ("Message pushed successfully", None),
        404: ("User not found or no connections", None)
    }, default=common_responses)
)
async def push_message(
    payload: UserPushRequest,
    ws_manager: Annotated[ConnectionManager, Depends(get_manager)]
):
    try:
        await push_message_to_user(payload.user_id, payload.type, payload.data, ws_manager)
        return APIResponse(code=200, message="Message pushed successfully")
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found or no connections")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/push-by-role",
    response_model=APIResponse[None],
    response_model_exclude_unset=True,
    summary="Push message to all connections of users with a specific role",
    responses=parse_responses({
        200: ("Message pushed successfully", None),
        404: ("No users with this role or no connections", None)
    }, default=common_responses)
)
async def push_message_by_role(
    payload: RolePushRequest,
    ws_manager: Annotated[ConnectionManager, Depends(get_manager)]
):
    try:
        count = await push_message_to_role(payload.role, payload.type, payload.data, ws_manager)
        if count == 0:
            raise HTTPException(status_code=404, detail="No users with this role or no connections")
        return APIResponse(code=200, message=f"Message pushed successfully, pushed {count} connections")
    except RoleNotFoundException:
        raise HTTPException(status_code=404, detail="No users with this role or no connections")
    except Exception:
        raise HTTPException(status_code=500)