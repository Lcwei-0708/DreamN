import os
import json
import logging
from datetime import datetime
from core.redis import get_redis
from core.dependencies import get_db
from websocket.manager import get_manager
from models.websocket_events import WebSocketEvents

ws_manager = get_manager()

class WebSocketSchedule:
    def __init__(self):
        self.logger = logging.getLogger("websocket_schedule")

    async def send_heartbeat_ping(self):
        """
        Send heartbeat ping to all active connections
        """
        try:
            sent, failed = await ws_manager.send_heartbeat_ping()
            if sent > 0 or failed > 0:
                self.logger.info(f"Heartbeat push completed - success: {sent}, failed: {failed}")
                
        except Exception as e:
            self.logger.error(f"Send heartbeat task failed: {e}")

    async def cleanup_expired_connections(self, timeout_seconds=60):
        """
        Clean up expired connections that have not responded to heartbeat
        Default timeout is 60 seconds
        """
        try:
            cleaned = await ws_manager.heartbeat_checker(timeout_seconds=timeout_seconds)
            if cleaned > 0:
                self.logger.info(f"Cleaned up expired connections - removed: {cleaned} connections")
                
        except Exception as e:
            self.logger.error(f"Cleanup expired connections task failed: {e}")

    async def batch_save_websocket_events(self, max_batch=1000):
        """
        Batch save WebSocket events to database
        Get events from Redis event queue and write to database
        """
        try:
            redis = get_redis()
            events = []
            
            for _ in range(max_batch):
                event_json = await redis.lpop("ws:event_queue")
                if not event_json:
                    break
                try:
                    event_data = json.loads(event_json)
                    events.append(event_data)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid event JSON format: {e}")
                    continue
            
            if events:
                saved_count = await self.save_events_to_db(events)
                self.logger.info(f"Batch save WebSocket events completed - saved: {saved_count} events")
                
        except Exception as e:
            self.logger.error(f"Batch save WebSocket events task failed: {e}")

    async def save_events_to_db(self, events):
        """
        Save event list to database
        Return the number of successfully saved events
        """
        try:
            async for db in get_db():
                objs = []
                for event in events:
                    try:
                        # Create WebSocketEvents object
                        event_obj = WebSocketEvents(
                            user_id=event["user_id"],
                            event_type=event["event_type"],
                            event_time=datetime.fromisoformat(event["time"]),
                            ip_address=event["ip"]
                        )
                        objs.append(event_obj)
                    except (KeyError, ValueError) as e:
                        self.logger.warning(f"Invalid event data format: {e}, event: {event}")
                        continue
                
                if objs:
                    db.add_all(objs)
                    await db.commit()
                    return len(objs)
                else:
                    return 0
                    
        except Exception as e:
            self.logger.error(f"Save events to database failed: {e}")
            return 0