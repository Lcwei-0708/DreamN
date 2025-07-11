from typing import Optional, List
from pydantic import BaseModel, Field

class IPDebugResponse(BaseModel):
    client_host: Optional[str] = Field(None, description="客戶端 host (remote_addr)")
    x_forwarded_for: Optional[str] = Field(None, description="X-Forwarded-For Header")
    x_real_ip: Optional[str] = Field(None, description="X-Real-IP Header")
    detected_real_ip: Optional[str] = Field(None, description="經 middleware 處理後的真實 IP")
    middleware_processed: bool = Field(..., description="middleware 是否有處理過")
    note: str = Field(..., description="備註/說明")

class ClearBlockedIPsResponse(BaseModel):
    cleared_ips: List[str] = Field(..., description="被清除封鎖的 IP 列表")
    count: int = Field(..., description="被清除的 IP 數量")