import uuid
from core.database import Base
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, text

class ModbusController(Base):
    __tablename__ = "modbus_controller"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="控制器 ID")
    name = Column(String(100), nullable=False, comment="控制器名稱")
    host = Column(String(64), nullable=False, comment="TCP 主機位址")
    port = Column(Integer, nullable=False, comment="TCP 連接埠")
    timeout = Column(Integer, nullable=False, comment="逾時秒數")
    status = Column(Boolean, nullable=False, default=False, comment="連線狀態 (True=已連線, False=未連線)")
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), comment="建立時間")
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment="更新時間")

    def __repr__(self):
        return f"<ModbusController id={self.id} name={self.name} host={self.host} port={self.port} status={self.status}>"