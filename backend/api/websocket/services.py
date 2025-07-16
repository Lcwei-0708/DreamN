import json
from datetime import datetime
from core.redis import get_redis
from websocket.manager import ConnectionManager
from .schema import OnlineUsersResponse, OnlineUserInfo, ConnectionInfo
from utils.custom_exception import ServerException, UserNotFoundException, RoleNotFoundException

async def fetch_online_users() -> OnlineUsersResponse:
    try:
        redis = get_redis()
        user_ids = await redis.smembers("ws:online_users")
        users = []
        total_connections = 0
        now = datetime.now().astimezone()
        for user_id in user_ids:
            conns = await redis.hgetall(f"ws:online_users:{user_id}")
            conn_list = []
            for sid, conn_json in conns.items():
                conn = json.loads(conn_json)
                connected_time = datetime.fromisoformat(conn["connected_time"])
                duration = (now - connected_time).total_seconds() / 60
                last_heartbeat = datetime.fromisoformat(conn["last_heartbeat"])
                heartbeat_ago = (now - last_heartbeat).total_seconds()
                conn_list.append(ConnectionInfo(
                    sid=sid,
                    connected_time=connected_time.isoformat(),
                    last_heartbeat=last_heartbeat.isoformat(),
                    connection_duration_minutes=f"{duration:.2f}",
                    last_heartbeat_seconds_ago=f"{heartbeat_ago:.0f}",
                    ip=conn["ip"]
                ))
            users.append(OnlineUserInfo(
                user_id=user_id,
                total_connections=len(conn_list),
                connections=conn_list
            ))
            total_connections += len(conn_list)
        return OnlineUsersResponse(
            total_users=len(users),
            total_connections=total_connections,
            users=users
        )
    except Exception as e:
        raise ServerException(f"Fetch online users failed: {str(e)}")

async def broadcast_message(msg_type: str, data, ws_manager: ConnectionManager):
    try:
        await ws_manager.broadcast(msg_type, data)
        return True
    except Exception as e:
        raise ServerException(f"Broadcast message failed: {str(e)}")

async def push_message_to_user(user_id: str, msg_type: str, data, ws_manager: ConnectionManager):
    try:
        is_pushed = await ws_manager.push_message_to_user(user_id, msg_type, data)
        if not is_pushed:
            raise UserNotFoundException(f"User {user_id} not found or no connections")
        return is_pushed
    except UserNotFoundException:
        raise
    except Exception as e:
        raise ServerException(f"Push message to user {user_id} failed: {str(e)}")

async def push_message_to_role(role: str, msg_type: str, data, ws_manager: ConnectionManager):
    try:
        count = await ws_manager.push_message_to_role(role, msg_type, data)
        return count
    except RoleNotFoundException:
        raise
    except Exception as e:
        raise ServerException(f"Push message to role {role} failed: {str(e)}")