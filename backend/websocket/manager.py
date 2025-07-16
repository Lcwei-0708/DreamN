import os
import json
import uuid
import logging
import asyncio
from datetime import datetime
from fastapi import WebSocket
from core.redis import get_redis
from sqlalchemy import select, asc
from extensions.keycloak import get_keycloak
from models.websocket_events import WebSocketEvents
from utils.get_real_ip import get_real_ip_websocket
from utils.custom_exception import RoleNotFoundException, UserNotFoundException

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self._redis_reset = False

    async def reset_redis_connections(self):
        """
        Reset all connection status in Redis
        """
        redis = get_redis()
        online_users = await redis.smembers("ws:online_users")
        
        for user_id in online_users:
            await redis.delete(f"ws:online_users:{user_id}")
            await redis.delete(f"ws:userinfo:{user_id}")        
        await redis.delete("ws:online_users")        
        self._redis_reset = True

    async def ensure_redis_reset(self):
        """
        Ensure Redis status is reset
        """
        if not self._redis_reset:
            await self.reset_redis_connections()

    async def connect(self, websocket: WebSocket, userinfo: dict):
        await self.ensure_redis_reset()
        
        await websocket.accept()
        sid = str(uuid.uuid4())
        ip = get_real_ip_websocket(websocket)
        
        now = datetime.now().astimezone().isoformat()
        conn_info = {
            "sid": sid,
            "user_id": userinfo.get("sub"),
            "email": userinfo.get("email", ""),
            "ip": ip,
            "connected_time": now,
            "last_heartbeat": now
        }
        self.active_connections[sid] = {
            **conn_info,
            "websocket": websocket
        }
        await self._add_online_user_redis(conn_info)
        await self.log_ws_event_to_redis("connect", userinfo.get("sub"), ip)
        return sid

    async def disconnect(self, sid):
        conn_info = self.active_connections.pop(sid, None)
        if conn_info:
            asyncio.create_task(self._remove_online_user_redis(conn_info))
            await self.log_ws_event_to_redis("disconnect", conn_info["user_id"], conn_info["ip"])

    async def _add_online_user_redis(self, conn_info):
        redis = get_redis()
        user_id = conn_info["user_id"]
        sid = conn_info["sid"]
        await redis.hset(f"ws:online_users:{user_id}", sid, json.dumps(conn_info))
        await redis.sadd("ws:online_users", user_id)
        await redis.set(f"ws:userinfo:{user_id}", json.dumps({
            "user_id": user_id,
            "email": conn_info["email"],
            "ip": conn_info["ip"]
        }))

    async def _remove_online_user_redis(self, conn_info):
        redis = get_redis()
        user_id = conn_info["user_id"]
        sid = conn_info["sid"]
        await redis.hdel(f"ws:online_users:{user_id}", sid)
        if not await redis.hlen(f"ws:online_users:{user_id}"):
            await redis.srem("ws:online_users", user_id)
            await redis.delete(f"ws:userinfo:{user_id}")    

    async def log_ws_event_to_redis(self, event_type, user_id, ip):
        redis = get_redis()
        event = {
            "event_type": event_type,
            "user_id": user_id,
            "ip": ip,
            "time": datetime.now().astimezone().isoformat()
        }
        await redis.rpush("ws:event_queue", json.dumps(event))

    async def send_heartbeat_ping(self):
        """
        Send heartbeat ping to all connections in Redis
        Returns (success_count, failed_count)
        """
        logger = logging.getLogger("websocket_heartbeat")
        
        sent = 0
        failed = 0
        process_id = os.getpid()
        now = datetime.now().astimezone().isoformat()
        
        redis = get_redis()
        online_users = await redis.smembers("ws:online_users")
        total_redis_connections = 0
        
        for user_id in online_users:
            user_connections = await redis.hgetall(f"ws:online_users:{user_id}")
            total_redis_connections += len(user_connections)
            
            for sid, conn_json in list(user_connections.items()):
                try:
                    conn_info = json.loads(conn_json)
                    
                    if sid in self.active_connections:
                        ws = self.active_connections[sid]["websocket"]
                        try:
                            await ws.send_text(json.dumps({"type": "ping"}))
                            await redis.hset(f"ws:online_users:{user_id}", sid, json.dumps(conn_info))
                            sent += 1

                        except Exception as e:
                            failed += 1
                            
                except Exception as e:
                    logger.error(f"[PID:{process_id}] Error processing SID {sid}: {e}")     
        return sent, failed

    async def update_heartbeat(self, sid, msg_type="ping"):
        """
        Update heartbeat status
        msg_type: "ping" means received ping from client, "pong" means received pong response from client
        """
        now = datetime.now().astimezone().isoformat()
        conn = self.active_connections.get(sid)
        if conn:
            conn["last_heartbeat"] = now
            
            if msg_type == "pong":            
                user_id = conn["user_id"]
                conn_info = {k: v for k, v in conn.items() if k != "websocket"}
                conn_info["last_heartbeat"] = now
            
            redis = get_redis()
            await redis.hset(f"ws:online_users:{user_id}", sid, json.dumps(conn_info))

    async def heartbeat_checker(self, timeout_seconds=60):
        """
        Check all connections and remove idle connections.
        Return the number of removed connections.
        """
        now = datetime.now().astimezone()
        to_remove = []
        for sid, conn in list(self.active_connections.items()):
            last_heartbeat = datetime.fromisoformat(conn["last_heartbeat"])
            if (now - last_heartbeat).total_seconds() > timeout_seconds:
                ws = conn["websocket"]
                try:
                    await ws.close()
                except Exception:
                    pass
                to_remove.append(sid)
        for sid in to_remove:
            await self.disconnect(sid)
        return len(to_remove)

    async def broadcast(self, msg_type: str, data):
        message = self.build_ws_message(msg_type, data)
        to_remove = []
        for sid, connection in self.active_connections.items():
            ws = connection["websocket"]
            try:
                await ws.send_text(message)
            except Exception:
                to_remove.append(sid)
        for sid in to_remove:
            await self.disconnect(sid)

    async def push_message_to_user(self, user_id: str, msg_type: str, data):
        redis = get_redis()
        conns = await redis.hgetall(f"ws:online_users:{user_id}")
        if not conns:
            return False
        message = self.build_ws_message(msg_type, data)
        for sid, conn_json in conns.items():
            ws = self.active_connections.get(sid, {}).get("websocket")
            if ws:
                try:
                    await ws.send_text(message)
                except Exception:
                    await self.disconnect(sid)
        return True

    async def push_message_to_role(self, role: str, msg_type: str, data, keycloak=None):
        if keycloak is None:
            keycloak = get_keycloak()
        try:
            users = await keycloak.keycloak_admin.a_get_realm_role_members(role, {})
        except Exception as e:
            raise RoleNotFoundException(f"Select Keycloak users failed: {e}")
        user_ids = [user['id'] for user in users]
        if not user_ids:
            raise UserNotFoundException(f"Role {role} has no users")
        count = 0
        message = self.build_ws_message(msg_type, data)
        for user_id in user_ids:
            redis = get_redis()
            conns = await redis.hgetall(f"ws:online_users:{user_id}")
            for sid, conn_json in conns.items():
                ws = self.active_connections.get(sid, {}).get("websocket")
                if ws:
                    try:
                        await ws.send_text(message)
                        count += 1
                    except Exception:
                        await self.disconnect(sid)
        return count
    
    @staticmethod
    def build_ws_message(msg_type: str, data):
        return json.dumps({
            "type": msg_type,
            "time": datetime.now().astimezone().isoformat(),
            "data": data
        })

    @staticmethod
    async def get_user_last_ws_login(user_id, db):
        """
        Get user's last WebSocket connection status and time.
        - If the user is still online, return (True, current time)
        - If the user is offline, return (False, last disconnect/timeout time)
        """
        stmt = (
            select(WebSocketEvents)
            .where(WebSocketEvents.user_id == user_id)
            .order_by(asc(WebSocketEvents.event_time))
        )
        result = await db.execute(stmt)
        events = result.scalars().all()

        online_count = 0
        last_disconnect_time = None
        for event in events:
            if event.event_type == "connect":
                online_count += 1
            elif event.event_type == "disconnect":
                online_count = max(0, online_count - 1)
                last_disconnect_time = event.event_time

        if online_count > 0:
            return True, datetime.now()
        else:
            return False, last_disconnect_time

# 全局實例（用於依賴注入）
_manager_instance = None

def get_manager() -> ConnectionManager:
    """
    獲取 ConnectionManager 實例的依賴函數
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ConnectionManager()
    return _manager_instance