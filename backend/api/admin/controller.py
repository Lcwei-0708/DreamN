from typing import Optional
from core.security import verify_token
from extensions.keycloak import get_keycloak
from core.dependencies import rate_limit_on_auth_fail
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from utils.response import APIResponse, parse_responses, common_responses
from .schema import (
    UserPagination, UserSortBy,
    CreateUserRequest, UpdateUserRequest, ResetPasswordRequest,
    RoleList, CreateRoleRequest, UpdateRoleRequest,
    RoleAttributesUpdateRequest, CreateRoleResponse, CreateUserResponse
)
from .services import (
    get_all_users, create_user, update_user, delete_user, reset_user_password,
    get_all_roles, create_role, update_role, delete_role, update_role_attributes
)
from utils.custom_exception import (
    UserNotFoundException,
    RoleNotFoundException,
    RoleAlreadyExistsException,
    EmailAlreadyExistsException
)

keycloak = get_keycloak()

router = APIRouter(tags=["admin"])

@router.get(
    "/users",
    response_model=APIResponse[UserPagination],
    summary="Get all users",
    description="Get all users (only admin can use)",
    responses=parse_responses({
        200: ("Successfully retrieved users", UserPagination),
        404: ("User not found", None)
    }, default=common_responses),
    dependencies=[Depends(rate_limit_on_auth_fail)]
)
@keycloak.require_permission("admin")
async def get_users(
    request: Request,
    token: str = Depends(verify_token),
    name: Optional[str] = Query(None, description="User name filter"),
    status: Optional[str] = Query(None, description="User status filter (multiple values separated by commas, e.g.: true,false)"),
    role: Optional[str] = Query(None, description="User role filter (multiple values separated by commas, e.g.: admin,manager)"),
    page: int = Query(1, ge=1, description="Page number (default: 1)"),
    per_page: int = Query(10, ge=1, le=100, description="Number of users per page (default: 10)"),
    sort_by: Optional[UserSortBy] = Query(None, description="Sorting field"),
    desc: bool = Query(False, description="Sorting order (default: false)")
):
    try:
        data = await get_all_users(
            name=name,
            status=status,
            role=role,
            page=page,
            per_page=per_page,
            sort_by=sort_by.value if sort_by else None,
            desc=desc
        )        
        return APIResponse(code=200, message="Successfully retrieved users", data=data)
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/users",
    response_model=APIResponse[CreateUserResponse],
    response_model_exclude_none=True,
    summary="Create new user",
    description="Create new user (only admin can use)",
    responses=parse_responses({
        200: ("User created successfully", CreateUserResponse),
        409: ("Email already exists", None)
    }, default=common_responses),
    dependencies=[Depends(rate_limit_on_auth_fail)]
)
@keycloak.require_permission("admin")
async def create_new_user(payload: CreateUserRequest, request: Request, token: str = Depends(verify_token)):
    try:
        user_id = await create_user(payload)
        return APIResponse(code=200, message="User created successfully", data=user_id)
    except EmailAlreadyExistsException:
        raise HTTPException(status_code=409, detail="Email already exists")
    except Exception:
        raise HTTPException(status_code=500)

@router.put(
    "/users/{user_id}",
    response_model=APIResponse[None],
    response_model_exclude_none=True,
    summary="Update user info",
    description="Update user info (only admin can use)",
    responses=parse_responses({
        200: ("User updated successfully", None),
        404: ("User not found", None),
        409: ("Email already exists", None)
    }, default=common_responses),
    dependencies=[Depends(rate_limit_on_auth_fail)]
)
@keycloak.require_permission("admin")
async def update_user_info(user_id: str, payload: UpdateUserRequest, request: Request, token: str = Depends(verify_token)):
    try:
        await update_user(user_id, payload)
        return APIResponse(code=200, message="User updated successfully")
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except EmailAlreadyExistsException:
        raise HTTPException(status_code=409, detail="Email already exists")
    except Exception:
        raise HTTPException(status_code=500)

@router.delete(
    "/users/{user_id}",
    response_model=APIResponse[None],
    response_model_exclude_none=True,
    summary="Delete user",
    description="Delete user (only admin can use)",
    responses=parse_responses({
        200: ("User deleted successfully", None),
        404: ("User not found", None)
    }, default=common_responses),
    dependencies=[Depends(rate_limit_on_auth_fail)]
)
@keycloak.require_permission("admin")
async def delete_user_by_id(user_id: str, request: Request, token: str = Depends(verify_token)):
    try:
        await delete_user(user_id)
        return APIResponse(code=200, message="User deleted successfully")
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/users/{user_id}/reset-password",
    response_model=APIResponse[None],
    response_model_exclude_none=True,
    summary="Reset user password",
    description="Reset user password (only admin can use)",
    responses=parse_responses({
        200: ("Password reset successfully", None),
        404: ("User not found", None)
    }, default=common_responses),
    dependencies=[Depends(rate_limit_on_auth_fail)]
)
@keycloak.require_permission("admin")
async def reset_password(user_id: str, payload: ResetPasswordRequest, request: Request, token: str = Depends(verify_token)):
    try:
        await reset_user_password(user_id, payload.password)
        return APIResponse(code=200, message="Password reset successfully")
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.get(
    "/roles",
    response_model=APIResponse[RoleList],
    summary="Get all custom roles",
    description="Get all custom roles (only admin can use)",
    responses=parse_responses({
        200: ("Successfully retrieved roles", RoleList),
        404: ("Role not found", None)
    }, default=common_responses),
    dependencies=[Depends(rate_limit_on_auth_fail)]
)
@keycloak.require_permission("admin")
async def get_roles(request: Request, token: str = Depends(verify_token)):
    try:
        roles = await get_all_roles()
        return APIResponse(code=200, message="Successfully retrieved roles", data=roles)
    except RoleNotFoundException:
        raise HTTPException(status_code=404, detail="Role not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/roles",
    response_model=APIResponse[CreateRoleResponse],
    response_model_exclude_none=True,
    summary="Create new role",
    description="Create new role (only admin can use)",
    responses=parse_responses({
        200: ("Role created successfully", CreateRoleResponse),
        409: ("Role name already exists", None)
    }, default=common_responses),
    dependencies=[Depends(rate_limit_on_auth_fail)]
)
@keycloak.require_permission("admin")
async def create_new_role(payload: CreateRoleRequest, request: Request, token: str = Depends(verify_token)):
    try:
        role_name = await create_role(payload)
        return APIResponse(code=200, message="Role created successfully", data=role_name)
    except RoleAlreadyExistsException:
        raise HTTPException(status_code=409, detail="Role name already exists")
    except Exception:
        raise HTTPException(status_code=500)

@router.put(
    "/roles/{role_name}",
    response_model=APIResponse[None],
    response_model_exclude_none=True,
    summary="Update role info",
    description="Update role info (only admin can use)",
    responses=parse_responses({
        200: ("Role updated successfully", None),
        404: ("Role not found", None)
    }, default=common_responses),
    dependencies=[Depends(rate_limit_on_auth_fail)]
)
@keycloak.require_permission("admin")
async def update_role_info(role_name: str, payload: UpdateRoleRequest, request: Request, token: str = Depends(verify_token)):
    try:
        await update_role(role_name, payload)
        return APIResponse(code=200, message="Role updated successfully")
    except RoleNotFoundException:
        raise HTTPException(status_code=404, detail="Role not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.put(
    "/roles/{role_name}/attributes",
    response_model=APIResponse[None],
    response_model_exclude_none=True,
    summary="Update role attributes",
    description="Update role attributes (only admin can use)",
    responses=parse_responses({
        200: ("Role attributes updated successfully", None),
        404: ("Role not found", None)
    }, default=common_responses),
    dependencies=[Depends(rate_limit_on_auth_fail)]
)
@keycloak.require_permission("admin")
async def update_role_attributes_api(role_name: str, payload: RoleAttributesUpdateRequest, request: Request, token: str = Depends(verify_token)):
    try:
        await update_role_attributes(role_name, payload.attributes)
        return APIResponse(code=200, message="Role attributes updated successfully")
    except RoleNotFoundException:
        raise HTTPException(status_code=404, detail="Role not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.delete(
    "/roles/{role_name}",
    response_model=APIResponse[None],
    response_model_exclude_none=True,
    summary="Delete role",
    description="Delete role (only admin can use)",
    responses=parse_responses({
        200: ("Role deleted successfully", None),
        404: ("Role not found", None)
    }, default=common_responses),
    dependencies=[Depends(rate_limit_on_auth_fail)]
)
@keycloak.require_permission("admin")
async def delete_role_by_name(role_name: str, request: Request, token: str = Depends(verify_token)):
    try:
        await delete_role(role_name)
        return APIResponse(code=200, message="Role deleted successfully")
    except RoleNotFoundException:
        raise HTTPException(status_code=404, detail="Role not found")
    except Exception:
        raise HTTPException(status_code=500)