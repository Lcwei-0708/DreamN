import uuid
from core.database import Base
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Float, TIMESTAMP, text

class ModbusPoint(Base):
    __tablename__ = "modbus_point"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="點位 ID")
    controller_id = Column(String(36), ForeignKey("modbus_controller.id"), nullable=False, comment="控制器 ID")
    name = Column(String(100), nullable=False, comment="點位名稱")
    description = Column(Text, comment="描述")
    type = Column(String(50), nullable=False, comment="點位型態 (coil/input/holding_register/input_register)")
    data_type = Column(String(50), nullable=False, comment="資料型態 (bool/int/float)")
    address = Column(Integer, nullable=False, comment="Modbus 位址")
    len = Column(Integer, nullable=False, comment="長度")
    unit_id = Column(Integer, nullable=False, default=1, comment="裝置 ID")
    formula = Column(Text, comment="轉換公式")
    unit = Column(String(32), comment="單位")
    min_value = Column(Float, comment="最小值")
    max_value = Column(Float, comment="最大值")
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), comment="建立時間")
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment="更新時間")

    def __repr__(self):
        return f"<ModbusPoint id={self.id} name={self.name} type={self.type} address={self.address} unit_id={self.unit_id}>"