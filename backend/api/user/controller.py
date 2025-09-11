from core.dependencies import get_db
from core.security import verify_token
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Request
from .schema import UserInfo, ChangePasswordRequest, UpdateUserRequest
from utils.response import APIResponse, parse_responses, common_responses
from .services import get_current_user_info, change_current_user_password, update_current_user_info
from utils.custom_exception import InvalidPasswordException, EmailAlreadyExistsException

router = APIRouter(tags=["user"])

@router.get(
    "/info",
    response_model=APIResponse[UserInfo],
    summary="Get current user info",
    responses=parse_responses({
        200: ("User info retrieved successfully", UserInfo)
    }, default=common_responses)
)
async def get_user_info(request: Request, token: str = Depends(verify_token), db: AsyncSession = Depends(get_db)):
    try:
        data = await get_current_user_info(token, db)
        return APIResponse(code=200, message="User info retrieved successfully", data=data)
    except Exception:
        raise HTTPException(status_code=500)

@router.put(
    "/update",
    response_model=APIResponse[None],
    response_model_exclude_none=True,
    summary="Update user info",
    responses=parse_responses({
        200: ("User info updated successfully", None),
        400: ("Failed to update user info", None),
        409: ("Email already exists", None),
    }, default=common_responses)
)
async def update_user(payload: UpdateUserRequest, token: str = Depends(verify_token)):
    try:
        await update_current_user_info(token, payload.dict(exclude_unset=True))
        return APIResponse(code=200, message="User info updated successfully", data=None)
    except EmailAlreadyExistsException:
        raise HTTPException(status_code=409, detail="Email already exists")
    except Exception:
        raise HTTPException(status_code=500)

@router.put(
    "/change-password",
    response_model=APIResponse[None],
    response_model_exclude_none=True,
    summary="Change user password",
    responses=parse_responses({
        200: ("Password changed successfully", None),
        401: ("Invalid or expired token / Old password is incorrect", None),
    }, default=common_responses)
)
async def change_password(payload: ChangePasswordRequest, token: str = Depends(verify_token)):
    try:
        await change_current_user_password(
            token, 
            payload.old_password, 
            payload.new_password,
            payload.logout_all_devices
        )
        return APIResponse(code=200, message="Password changed successfully", data=None)
    except InvalidPasswordException:
        raise HTTPException(status_code=401, detail="Old password is incorrect")
    except Exception:
        raise HTTPException(status_code=500)