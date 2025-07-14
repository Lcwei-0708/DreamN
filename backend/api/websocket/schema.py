from typing import List, Any, Dict
from pydantic import BaseModel, Field

class ConnectionInfo(BaseModel):
    sid: str = Field(..., description="連線 ID")
    connected_time: str = Field(..., description="連線時間")
    last_heartbeat: str = Field(..., description="最後心跳時間")
    connection_duration_minutes: str = Field(..., description="連線時長 (分鐘)")
    last_heartbeat_seconds_ago: str = Field(..., description="最後心跳時間 (秒)")
    ip: str = Field(..., description="連線 IP")

class OnlineUserInfo(BaseModel):
    user_id: str = Field(..., description="使用者 ID")
    total_connections: int = Field(..., description="總連線數")
    connections: List[ConnectionInfo] = Field(..., description="連線列表")

class OnlineUsersResponse(BaseModel):
    total_users: int = Field(..., description="總使用者數量")
    total_connections: int = Field(..., description="總連線數")
    users: List[OnlineUserInfo] = Field(..., description="使用者列表")

class BroadcastRequest(BaseModel):
    type: str = Field(..., description="訊息類型", example="info")
    data: Dict = Field(
        ..., 
        description="訊息內容", 
        example={"message": "Hello, world!"}
    )

class UserPushRequest(BaseModel):
    user_id: str = Field(..., description="要推播的使用者 ID", example="user_001")
    type: str = Field(..., description="訊息類型", example="info")
    data: Dict = Field(
        ..., 
        description="訊息內容", 
        example={"message": "Hello, world!"}
    )

class RolePushRequest(BaseModel):
    role: str = Field(..., description="要推播的 Keycloak 角色", example="admin")
    type: str = Field(..., description="訊息類型", example="info")
    data: Dict = Field(
        ..., 
        description="訊息內容", 
        example={"message": "Hello, world!"}
    )

online_users_response_example = {
    "code": 200,
    "message": "Get online users successfully",
    "data": {
        "total_users": 1,
        "total_connections": 2,
        "users": [
            {
                "user_id": "user_001",
                "total_connections": 2,
                "connections": [
                    {
                        "sid": "abc123",
                        "connected_time": "2024-06-01T12:00:00+00:00",
                        "last_heartbeat": "2024-06-01T12:05:00+00:00",
                        "connection_duration_minutes": "5.00",
                        "last_heartbeat_seconds_ago": "60",
                        "ip": "127.0.0.1"
                    },
                    {
                        "sid": "def456",
                        "connected_time": "2024-06-01T12:01:00+00:00",
                        "last_heartbeat": "2024-06-01T12:06:00+00:00",
                        "connection_duration_minutes": "5.00",
                        "last_heartbeat_seconds_ago": "60",
                        "ip": "127.0.0.1"
                    }
                ]
            }
        ]
    }
}