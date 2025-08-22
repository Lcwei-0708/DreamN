from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

class UserInfo(BaseModel):
    id: str = Field(..., description="使用者 ID")
    username: str = Field(..., description="帳號")
    firstName: str = Field(..., description="名字")
    lastName: str = Field(..., description="姓氏")
    email: Optional[EmailStr] = Field(None, description="電子信箱")
    phone: Optional[str] = Field(None, description="電話")
    enabled: bool = Field(..., description="帳號是否啟用")
    roles: List[str] = Field(..., description="角色列表")
    lastLogin: Optional[str] = Field(None, description="最後登入時間")

class UpdateUserRequest(BaseModel):
    firstName: Optional[str] = Field(None, description="名字")
    lastName: Optional[str] = Field(None, description="姓氏")
    email: Optional[EmailStr] = Field(None, description="電子信箱")
    phone: Optional[str] = Field(None, description="電話")

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="舊密碼")
    new_password: str = Field(..., description="新密碼")
    logout_all_devices: bool = Field(True, description="是否登出所有裝置")