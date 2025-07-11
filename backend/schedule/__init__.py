from core.database import engine
from .websocket_schedule import WebSocketSchedule
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from functools import partial

executors = {
    'default': AsyncIOExecutor(),
}
jobstores = {
    'default': SQLAlchemyJobStore(engine=engine)
}
scheduler = AsyncIOScheduler(jobstores=jobstores, executors=executors)

websocket_schedule = WebSocketSchedule()

def register_schedules():
    scheduler.add_job(
        websocket_schedule.send_heartbeat_ping,
        "interval",
        seconds=60,
        id="send_heartbeat_ping",
        replace_existing=True,
        max_instances=1
    )
    
    scheduler.add_job(
        websocket_schedule.cleanup_expired_connections,
        "interval",
        seconds=300,
        args=[600],  # timeout_seconds=600
        id="cleanup_expired_connections",
        replace_existing=True,
        max_instances=1
    )
    
    scheduler.add_job(
        websocket_schedule.batch_save_websocket_events, 
        "interval", 
        seconds=60,
        id="batch_save_websocket_events",
        replace_existing=True,
        max_instances=1
    )