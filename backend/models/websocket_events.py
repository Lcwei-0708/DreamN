import uuid
from core.database import Base
from sqlalchemy import Column, String, TIMESTAMP, text

class WebSocketEvents(Base):
    __tablename__ = "websocket_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="事件 ID")
    user_id = Column(String(36), nullable=False, comment="使用者 ID")
    event_type = Column(String(50), nullable=False, comment="事件類型")
    event_time = Column(TIMESTAMP, nullable=False, comment="事件時間")
    ip_address = Column(String(50), nullable=True, comment="連線 IP")
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), comment="建立時間")
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment="更新時間")

    def __repr__(self):
        return f"<WebSocketEvents user_id={self.user_id} event_type={self.event_type} event_time={self.event_time} ip_address={self.ip_address}>"