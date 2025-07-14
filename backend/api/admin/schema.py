from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, EmailStr, Field

class UserInfo(BaseModel):
    id: str = Field(..., description="使用者 ID")
    username: str = Field(..., description="帳號")
    firstName: str = Field(..., description="名字")
    lastName: str = Field(..., description="姓氏")
    email: Optional[str] = Field(None, description="電子信箱")
    phone: Optional[str] = Field(None, description="電話")
    enabled: bool = Field(..., description="帳號是否啟用")
    roles: List[str] = Field(default_factory=list, description="角色列表")
    lastLogin: Optional[str] = Field(None, description="最後登入時間")

class UserPagination(BaseModel):
    page: int = Field(..., description="當前頁碼")
    pages: int = Field(..., description="總頁數")
    per_page: int = Field(..., description="每頁顯示數量")
    total: int = Field(..., description="總使用者數量")
    users: List[UserInfo] = Field(..., description="使用者列表")

class UserSortBy(str, Enum):
    username = "username"
    firstName = "firstName"
    lastName = "lastName"
    email = "email"
    phone = "phone"
    enabled = "enabled"
    lastLogin = "lastLogin"

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="帳號")
    email: EmailStr = Field(..., description="電子信箱")
    firstName: Optional[str] = Field(None, max_length=50, description="名字")
    lastName: Optional[str] = Field(None, max_length=50, description="姓氏")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    password: str = Field(..., min_length=6, description="密碼")
    enabled: bool = Field(True, description="帳號是否啟用")

class CreateUserResponse(BaseModel):
    user_id: str = Field(..., description="使用者 ID")

class UpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = Field(None, description="電子信箱")
    firstName: Optional[str] = Field(None, max_length=50, description="名字")
    lastName: Optional[str] = Field(None, max_length=50, description="姓氏")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    enabled: Optional[bool] = Field(None, description="帳號是否啟用")

class ResetPasswordRequest(BaseModel):
    password: str = Field(..., description="新密碼")

class RoleInfo(BaseModel):
    id: str = Field(..., description="角色 ID")
    role_name: str = Field(..., description="角色名稱")
    description: Optional[str] = Field(None, description="角色描述")
    attributes: Optional[Dict[str, List[str]]] = Field(None, description="角色屬性")

class RoleList(BaseModel):
    roles: List[RoleInfo] = Field(..., description="角色列表")

class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="角色名稱")
    description: Optional[str] = Field(None, max_length=200, description="角色描述")

class CreateRoleResponse(BaseModel):
    role_name: str = Field(..., description="角色名稱")

class UpdateRoleRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=200, description="角色描述")

class RoleAttributesUpdateRequest(BaseModel):
    attributes: Dict[str, List[str]] = Field(..., description="角色屬性", example={"key_1": ["value_1"]})