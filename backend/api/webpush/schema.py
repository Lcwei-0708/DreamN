from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class WebPushSubscriptionRequest(BaseModel):
    endpoint: str = Field(..., description="訂閱的 Endpoint")
    keys: Dict[str, str] = Field(..., description="訂閱的 Keys")
    user_agent: Optional[str] = Field(None, description="使用者代理")

class WebPushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(..., description="取消訂閱的 Endpoint")

class WebPushSubscriptionResponse(BaseModel):
    id: str = Field(..., description="訂閱 ID")
    endpoint: str = Field(..., description="訂閱的 Endpoint")

class WebPushSubscriptionInfo(BaseModel):
    id: str = Field(..., description="訂閱 ID")
    endpoint: str = Field(..., description="訂閱的 Endpoint")
    keys: Dict[str, str] = Field(..., description="訂閱的 Keys")
    is_active: bool = Field(..., description="是否有效")
    user_agent: str = Field(..., description="使用者代理")
    created_at: str = Field(..., description="建立時間")
    updated_at: str = Field(..., description="更新時間")

class UserWebPushInfo(BaseModel):
    user_id: str = Field(..., description="使用者 ID")
    total_subscriptions: int = Field(..., description="訂閱數")
    subscriptions: List[WebPushSubscriptionInfo] = Field(..., description="訂閱列表")

class WebPushSubscriptionsResponse(BaseModel):
    total_users: int = Field(..., description="總使用者數量")
    total_subscriptions: int = Field(..., description="總訂閱數")
    users: List[UserWebPushInfo] = Field(..., description="使用者列表")

class WebPushMessageData(BaseModel):
    title: str = Field(..., description="推播標題", example="Test")
    content: str = Field(..., description="推播內容", example="Hello, world!")
    url: str = Field(..., description="點擊後導向的網址", example="https://example.com")

class WebPushSendRequest(BaseModel):
    data: WebPushMessageData = Field(..., description="推播資料")

class WebPushUserSendRequest(BaseModel):
    user_id: str = Field(..., description="要推播的使用者 ID")
    data: WebPushMessageData = Field(..., description="推播資料")

class WebPushRoleSendRequest(BaseModel):
    role: str = Field(..., description="要推播的 Keycloak 角色")
    data: WebPushMessageData = Field(..., description="推播資料")

class WebPushSendResult(BaseModel):
    total: int = Field(..., description="實際推播的 endpoint 數")
    success: int = Field(..., description="推播成功的 endpoint 數")
    fail: int = Field(..., description="推播失敗的 endpoint 數")

webpush_subscriptions_response_example = {
    "code": 200,
    "message": "List all subscriptions successfully",
    "data": {
        "total_users": 2,
        "total_subscriptions": 3,
        "users": [
            {
                "user_id": "user_001",
                "total_subscriptions": 2,
                "subscriptions": [
                    {
                        "id": "subid1",
                        "endpoint": "https://example.com/1",
                        "keys": {
                            "p256dh": "p256dh_key_1",
                            "auth": "auth_key_1"
                        },
                        "created_at": "2024-06-01T12:00:00+00:00",
                        "updated_at": "2024-06-01T12:05:00+00:00"
                    },
                    {
                        "id": "subid2",
                        "endpoint": "https://example.com/2",
                        "keys": {
                            "p256dh": "p256dh_key_2",
                            "auth": "auth_key_2"
                        },
                        "created_at": "2024-06-01T12:10:00+00:00",
                        "updated_at": "2024-06-01T12:15:00+00:00"
                    }
                ]
            },
            {
                "user_id": "user_002",
                "total_subscriptions": 1,
                "subscriptions": [
                    {
                        "id": "subid3",
                        "endpoint": "https://example.com/3",
                        "keys": {
                            "p256dh": "p256dh_key_3",
                            "auth": "auth_key_3"
                        },
                        "created_at": "2024-06-01T13:00:00+00:00",
                        "updated_at": "2024-06-01T13:05:00+00:00"
                    }
                ]
            }
        ]
    }
}

webpush_subscription_request_example = {
    "endpoint": "string",
    "keys": {
        "p256dh": "string",
        "auth": "string"
    },
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

webpush_send_result_example = {
    "total": 5,
    "success": 4,
    "fail": 1
}

webpush_send_role_result_example = {
    "total": 8,
    "success": 7,
    "fail": 1,
    "user_count": 3
}