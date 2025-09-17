import uuid
from core.database import Base
from sqlalchemy import Column, String, JSON, Text, Boolean, TIMESTAMP, text

class WebPushSubscription(Base):
    __tablename__ = "webpush_subscription"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="訂閱 ID")
    user_id = Column(String(36), nullable=False, comment="使用者 ID")
    endpoint = Column(Text, nullable=False, unique=True, comment="訂閱的 Endpoint")
    keys = Column(JSON, nullable=False, comment="訂閱的 Keys")
    is_active = Column(Boolean, default=True, comment="是否有效")
    user_agent = Column(String(255), nullable=False, comment="使用者代理")
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), comment="建立時間")
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment="更新時間")

    def __repr__(self):
        return f"<WebPushSubscription user_id={self.user_id} endpoint={self.endpoint}>"