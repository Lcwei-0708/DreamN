import math
from core.config import settings
from typing import Optional, List
from websocket.manager import get_manager
from extensions.keycloak import get_keycloak
from sqlalchemy.ext.asyncio import AsyncSession
from utils.custom_exception import (
    UserNotFoundException,
    EmailAlreadyExistsException,
    RoleNotFoundException,
    RoleAlreadyExistsException,
    ServerException,
    SuperRoleOperationException
)
from .schema import (UserInfo, 
    UserPagination, 
    CreateUserRequest, 
    CreateUserResponse,
    UpdateUserRequest, 
    RoleInfo, 
    CreateRoleRequest, 
    CreateRoleResponse, 
    UpdateRoleRequest, 
    RoleList,
    DeleteUsersResponse
)

ws_manager = get_manager()
keycloak = get_keycloak()
keycloak_openid = keycloak.keycloak_openid
keycloak_admin = keycloak.keycloak_admin

def has_super_role(user_roles: List[str]) -> bool:
    """Check if user has super role"""
    return settings.KEYCLOAK_SUPER_ROLE in user_roles

async def get_all_users(
    db: AsyncSession,
    name: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
    sort_by: Optional[str] = None,
    desc: bool = False
) -> UserPagination:
    """Get all users, support filtering, pagination and sorting"""
    try:
        # Get all users
        users = await keycloak_admin.a_get_users()
        user_list = []
        
        # Process each user data
        for user in users:
            # Get user's realm roles
            user_roles = await keycloak_admin.a_get_realm_roles_of_user(user["id"])
            realm_role_names = [role["name"] for role in user_roles]
            
            # Filter custom roles only
            custom_roles = [r for r in realm_role_names if keycloak.is_custom_role(r)]
            
            # Skip users with super role
            if has_super_role(custom_roles):
                continue
            
            # Get last login status and time
            _, last_login_dt = await ws_manager.get_user_last_ws_login(user["id"], db)
            if last_login_dt:
                last_login = last_login_dt.astimezone().isoformat()
            else:
                last_login = None
            
            # Get phone number (possibly in attributes)
            phone = None
            if user.get("attributes") and "phone" in user["attributes"]:
                phone_list = user["attributes"]["phone"]
                phone = phone_list[0] if phone_list and len(phone_list) > 0 else None
            
            user_info = UserInfo(
                id=user["id"],
                username=user.get("username", ""),
                firstName=user.get("firstName", ""),
                lastName=user.get("lastName", ""),
                email=user.get("email"),
                phone=phone,
                enabled=user.get("enabled", True),
                roles=custom_roles,
                lastLogin=last_login
            )
            user_list.append(user_info)
        
        # Apply filter conditions
        filtered_users = user_list
        
        # Filter by name (search firstName, lastName, username)
        if name:
            name_lower = name.lower()
            filtered_users = [
                user for user in filtered_users
                if (name_lower in user.firstName.lower() if user.firstName else False) or
                   (name_lower in user.lastName.lower() if user.lastName else False) or
                   (name_lower in user.username.lower() if user.username else False)
            ]
        
        # Filter by status
        if status:
            status_list = [s.strip().lower() == 'true' for s in status.split(',')]
            if len(status_list) == 1:
                # Only one status condition
                filtered_users = [user for user in filtered_users if user.enabled == status_list[0]]
        
        # Filter by role
        if role:
            role_list = [r.strip() for r in role.split(',')]
            filtered_users = [
                user for user in filtered_users
                if any(user_role in role_list for user_role in user.roles)
            ]
        
        # Calculate total
        total = len(filtered_users)
        
        # Sort
        if sort_by:
            reverse = desc
            if sort_by == "username":
                filtered_users.sort(key=lambda x: x.username or "", reverse=reverse)
            elif sort_by == "firstName":
                filtered_users.sort(key=lambda x: x.firstName or "", reverse=reverse)
            elif sort_by == "lastName":
                filtered_users.sort(key=lambda x: x.lastName or "", reverse=reverse)
            elif sort_by == "email":
                filtered_users.sort(key=lambda x: x.email or "", reverse=reverse)
            elif sort_by == "phone":
                filtered_users.sort(key=lambda x: x.phone or "", reverse=reverse)
            elif sort_by == "enabled":
                filtered_users.sort(key=lambda x: x.enabled, reverse=reverse)
            elif sort_by == "lastLogin":
                filtered_users.sort(key=lambda x: x.lastLogin or "", reverse=reverse)
        
        # Pagination
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_users = filtered_users[start_index:end_index]
        
        return UserPagination(
            page=page,
            pages=total_pages,
            per_page=per_page,
            total=total,
            users=paginated_users
        )
        
    except Exception as e:
        raise ServerException(f"Failed to get users: {str(e)}")

async def create_user(user_data: CreateUserRequest) -> CreateUserResponse:
    """Create a new user"""
    try:
        # Check if trying to assign super role
        if hasattr(user_data, 'roles') and user_data.roles and settings.KEYCLOAK_SUPER_ROLE in user_data.roles:
            raise SuperRoleOperationException("Cannot assign super role to new user")
        
        # Prepare attributes
        attributes = {}
        if user_data.phone:
            attributes["phone"] = [user_data.phone]
        
        user_payload = {
            "username": user_data.username,
            "email": user_data.email,
            "firstName": user_data.firstName,
            "lastName": user_data.lastName,
            "enabled": user_data.enabled,
            "emailVerified": False,
            "credentials": [{
                "type": "password",
                "value": user_data.password,
                "temporary": True
            }]
        }
        
        # Add attributes only if present
        if attributes:
            user_payload["attributes"] = attributes
        
        user_id = await keycloak_admin.a_create_user(user_payload)
        return CreateUserResponse(user_id=user_id)
    except SuperRoleOperationException:
        raise
    except Exception as e:
        if "exists" in str(e).lower():
            raise EmailAlreadyExistsException("username or email", f"{user_data.username}/{user_data.email}")
        raise ServerException(f"Failed to create user: {str(e)}")

async def update_user(user_id: str, user_data: UpdateUserRequest) -> None:
    """Update user information"""
    try:
        # Check if user has super role
        current_user = await keycloak_admin.a_get_user(user_id)
        user_roles = await keycloak_admin.a_get_realm_roles_of_user(user_id)
        current_roles = [role["name"] for role in user_roles]
        custom_roles = [r for r in current_roles if keycloak.is_custom_role(r)]
        
        if has_super_role(custom_roles):
            raise SuperRoleOperationException("Cannot modify super role user")
        
        # Check if trying to assign super role
        if hasattr(user_data, 'roles') and user_data.roles and settings.KEYCLOAK_SUPER_ROLE in user_data.roles:
            raise SuperRoleOperationException("Cannot assign super role to user")
        
        update_payload = user_data.dict(exclude_unset=True)
        # Check if email has changed
        if "email" in update_payload:
            current_email = current_user.get("email")
            new_email = update_payload["email"]
            if new_email and new_email != current_email:
                users_with_email = await keycloak_admin.a_get_users({"email": new_email})
                if users_with_email and any(u["id"] != user_id for u in users_with_email):
                    raise EmailAlreadyExistsException(f"email: {new_email}")
        # Handle phone field, move it to attributes
        if "phone" in update_payload:
            phone = update_payload.pop("phone")
            if phone is not None:
                update_payload.setdefault("attributes", {})
                update_payload["attributes"]["phone"] = [phone]
            else:
                # If phone is None, remove the attribute
                update_payload.setdefault("attributes", {})
                update_payload["attributes"]["phone"] = []
        await keycloak_admin.a_update_user(user_id, update_payload)
    except SuperRoleOperationException:
        raise
    except EmailAlreadyExistsException:
        raise
    except Exception as e:
        error_str = str(e)
        if keycloak.is_keycloak_404_error(error_str):
            raise UserNotFoundException(f"user_id: {user_id}")
        raise ServerException(f"Failed to update user {user_id}: {str(e)}")

async def delete_users(user_ids: List[str]) -> DeleteUsersResponse:
    """Delete multiple users"""
    results = []
    
    for user_id in user_ids:
        try:
            # Check if user has super role
            user_roles = await keycloak_admin.a_get_realm_roles_of_user(user_id)
            current_roles = [role["name"] for role in user_roles]
            custom_roles = [r for r in current_roles if keycloak.is_custom_role(r)]
            
            if has_super_role(custom_roles):
                results.append({
                    "id": user_id,
                    "status": "error",
                    "message": "Cannot delete super role user"
                })
                continue
            
            await keycloak_admin.a_delete_user(user_id)
            results.append({
                "id": user_id,
                "status": "success",
                "message": "Deleted Successfully"
            })
        except Exception as e:
            error_str = str(e)
            if keycloak.is_keycloak_404_error(error_str):
                results.append({
                    "id": user_id,
                    "status": "not_found",
                    "message": "User not found"
                })
            else:
                results.append({
                    "id": user_id,
                    "status": "error",
                    "message": "Server error"
                })
    
    deleted_count = len([r for r in results if r["status"] == "success"])
    failed_count = len([r for r in results if r["status"] != "success"])
    
    return DeleteUsersResponse(
        total_requested=len(user_ids),
        deleted_count=deleted_count,
        failed_count=failed_count,
        results=results
    )

async def reset_user_password(user_id: str, new_password: str, logout_all_devices: bool = True) -> None:
    """Reset user password"""
    try:
        # Check if user has super role
        user_roles = await keycloak_admin.a_get_realm_roles_of_user(user_id)
        current_roles = [role["name"] for role in user_roles]
        custom_roles = [r for r in current_roles if keycloak.is_custom_role(r)]
        
        if has_super_role(custom_roles):
            raise SuperRoleOperationException("Cannot reset password for super role user")
        
        await keycloak_admin.a_set_user_password(user_id, new_password, temporary=True)
        if logout_all_devices:
            try:
                await keycloak_admin.a_user_logout(user_id)
            except Exception as e:
                raise ServerException(f"Failed to logout all devices: {str(e)}")
    except SuperRoleOperationException:
        raise
    except Exception as e:
        error_str = str(e)
        if keycloak.is_keycloak_404_error(error_str):
            raise UserNotFoundException(f"user_id: {user_id}")
        raise ServerException(f"Failed to reset password for user {user_id}: {str(e)}")

async def get_all_roles() -> RoleList:
    """Get all roles"""
    try:
        roles = await keycloak_admin.a_get_realm_roles()
        role_list = []
        for role in roles:
            if not keycloak.is_custom_role(role["name"]):
                continue
            
            # Skip super role
            if role["name"] == settings.KEYCLOAK_SUPER_ROLE:
                continue
            
            full_role = await keycloak_admin.a_get_realm_role(role["name"])
            role_info = RoleInfo(
                id=role["id"],
                role_name=role["name"],
                description=role.get("description"),
                attributes=keycloak.parse_attributes(full_role.get("attributes"))
            )
            role_list.append(role_info)
        return RoleList(roles=role_list)
    except Exception as e:
        raise ServerException(f"Failed to get roles: {str(e)}")

async def create_role(role_data: CreateRoleRequest) -> CreateRoleResponse:
    """Create a new role"""
    try:
        # Check if trying to create super role
        if role_data.name == settings.KEYCLOAK_SUPER_ROLE:
            raise SuperRoleOperationException("Cannot create super role")
        
        role_payload = {
            "name": role_data.name,
            "description": role_data.description,
        }
        await keycloak_admin.a_create_realm_role(role_payload)
        return CreateRoleResponse(role_name=role_data.name)
    except SuperRoleOperationException:
        raise
    except Exception as e:
        error_str = str(e)
        if keycloak.is_keycloak_409_error(error_str):
            raise RoleAlreadyExistsException(f"role_name: {role_data.name}")
        raise ServerException(f"Failed to create role {role_data.name}: {str(e)}")

async def update_role(role_name: str, role_data: UpdateRoleRequest) -> None:
    """Update role description only"""
    try:
        # Check if trying to update super role
        if role_name == settings.KEYCLOAK_SUPER_ROLE:
            raise SuperRoleOperationException("Cannot update super role")
        
        existing_role = await keycloak_admin.a_get_realm_role(role_name)
        update_payload = {
            "name": role_name,
            "description": role_data.description if role_data.description is not None else existing_role.get("description"),
        }
        await keycloak_admin.a_update_realm_role(role_name, update_payload)
    except SuperRoleOperationException:
        raise
    except Exception as e:
        error_str = str(e)
        if keycloak.is_keycloak_404_error(error_str):
            raise RoleNotFoundException(role_name)
        raise ServerException(f"Failed to update role {role_name}: {str(e)}")

async def update_role_attributes(role_name: str, attributes: dict) -> None:
    """Update role attributes only - merge with existing attributes"""
    try:
        # Check if trying to update super role
        if role_name == settings.KEYCLOAK_SUPER_ROLE:
            raise SuperRoleOperationException("Cannot update super role attributes")
        
        existing_role = await keycloak_admin.a_get_realm_role(role_name)        
        existing_attributes = existing_role.get("attributes", {})
        
        merged_attributes = existing_attributes.copy()
        merged_attributes.update(keycloak.format_attributes(attributes))
        
        update_payload = {
            "name": role_name,
            "description": existing_role.get("description", ""),
            "composite": existing_role.get("composite", False),
            "clientRole": existing_role.get("clientRole", False),
            "containerId": existing_role.get("containerId"),
            "attributes": merged_attributes
        }
        
        update_payload = {k: v for k, v in update_payload.items() if v is not None}
        
        await keycloak_admin.a_update_realm_role(role_name, update_payload)
    except SuperRoleOperationException:
        raise
    except Exception as e:
        error_str = str(e)
        if keycloak.is_keycloak_404_error(error_str):
            raise RoleNotFoundException(role_name)
        raise ServerException(f"Failed to update role attributes for {role_name}: {str(e)}")

async def delete_role(role_name: str) -> None:
    """Delete role"""
    try:
        # Check if trying to delete super role
        if role_name == settings.KEYCLOAK_SUPER_ROLE:
            raise SuperRoleOperationException("Cannot delete super role")
        
        await keycloak_admin.a_delete_realm_role(role_name)
    except SuperRoleOperationException:
        raise
    except Exception as e:
        error_str = str(e)
        if keycloak.is_keycloak_404_error(error_str):
            raise RoleNotFoundException(f"role_name: {role_name}")
        raise ServerException(f"Failed to delete role {role_name}: {str(e)}")