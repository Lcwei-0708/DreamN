from typing import Optional, List, Literal, Union, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class PointType(str, Enum):
    coil = "coil"
    input = "input"
    holding_register = "holding_register"
    input_register = "input_register"

class ConfigFormat(str, Enum):
    native = "native"
    thingsboard = "thingsboard"

class ModbusControllerCreateRequest(BaseModel):
    name: str = Field(..., description="控制器名稱", example="Test")
    host: str = Field(..., description="TCP 主機地址", example="192.168.1.100")
    port: int = Field(502, description="TCP 端口", example=502)
    timeout: int = Field(10, description="超時時間（秒）", example=10)

class ModbusControllerUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="控制器名稱", example="Test")
    host: Optional[str] = Field(None, description="TCP 主機地址", example="192.168.1.100")
    port: Optional[int] = Field(None, description="TCP 端口", example=502)
    timeout: Optional[int] = Field(None, description="超時時間（秒）", example=10)

class ModbusControllerResponse(BaseModel):
    id: str = Field(..., description="控制器 ID")
    name: str = Field(..., description="控制器名稱")
    host: str = Field(..., description="TCP 主機地址")
    port: int = Field(..., description="TCP 端口")
    timeout: int = Field(..., description="超時時間（秒）")
    status: bool = Field(..., description="控制器狀態")
    created_at: str = Field(..., description="建立時間")
    updated_at: str = Field(..., description="更新時間")

class ModbusControllerListResponse(BaseModel):
    total: int = Field(..., description="總數量")
    controllers: List[ModbusControllerResponse] = Field(..., description="控制器列表")

class ModbusPointCreateRequest(BaseModel):
    name: str = Field(..., description="點位名稱", example="Temperature 1")
    description: Optional[str] = Field(None, description="描述", example="鍋爐溫度感測器")
    type: PointType = Field(..., description="點位類型")
    data_type: str = Field(..., description="資料類型", example="uint16")
    address: int = Field(..., description="Modbus 地址", example=40001)
    len: int = Field(1, description="長度", example=1)
    unit_id: int = Field(1, description="單元 ID", example=1)
    formula: Optional[str] = Field(None, description="轉換公式", example="x * 0.1")
    unit: Optional[str] = Field(None, description="單位", example="°C")
    min_value: Optional[float] = Field(None, description="最小值", example=0.0)
    max_value: Optional[float] = Field(None, description="最大值", example=100.0)

class ModbusPointBatchCreateRequest(BaseModel):
    controller_id: str = Field(..., description="控制器 ID")
    points: List[ModbusPointCreateRequest] = Field(..., description="點位列表")

class ModbusPointUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="點位名稱")
    description: Optional[str] = Field(None, description="描述")
    type: Optional[PointType] = Field(None, description="點位類型")
    data_type: Optional[str] = Field(None, description="資料類型")
    address: Optional[int] = Field(None, description="Modbus 地址")
    len: Optional[int] = Field(None, description="長度")
    unit_id: Optional[int] = Field(None, description="單元 ID")
    formula: Optional[str] = Field(None, description="轉換公式")
    unit: Optional[str] = Field(None, description="單位")
    min_value: Optional[float] = Field(None, description="最小值")
    max_value: Optional[float] = Field(None, description="最大值")

class ModbusPointResponse(BaseModel):
    id: str = Field(..., description="點位 ID")
    controller_id: str = Field(..., description="控制器 ID")
    name: str = Field(..., description="點位名稱")
    description: Optional[str] = Field(None, description="描述")
    type: str = Field(..., description="點位類型")
    data_type: str = Field(..., description="資料類型")
    address: int = Field(..., description="Modbus 地址")
    len: int = Field(..., description="長度")
    unit_id: int = Field(..., description="單元 ID")
    formula: Optional[str] = Field(None, description="轉換公式")
    unit: Optional[str] = Field(None, description="單位")
    min_value: Optional[float] = Field(None, description="最小值")
    max_value: Optional[float] = Field(None, description="最大值")
    created_at: str = Field(..., description="建立時間")
    updated_at: str = Field(..., description="更新時間")

class ModbusPointListResponse(BaseModel):
    total: int = Field(..., description="總數量")
    points: List[ModbusPointResponse] = Field(..., description="點位列表")

class ModbusPointBatchCreateResponse(BaseModel):
    total: int = Field(..., description="總建立數量")
    points: List[ModbusPointResponse] = Field(..., description="已建立點位列表")

class ModbusPointDataResponse(BaseModel):
    point_id: str = Field(..., description="點位 ID")
    point_name: str = Field(..., description="點位名稱")
    controller_name: str = Field(..., description="控制器名稱")
    raw_data: List[Union[bool, int]] = Field(..., description="原始資料")
    converted_value: Union[bool, int, float, List] = Field(..., description="轉換後數值")
    final_value: Union[bool, int, float, List] = Field(..., description="最終數值（套用公式後）")
    data_type: str = Field(..., description="資料類型")
    unit: Optional[str] = Field(None, description="單位")
    formula: Optional[str] = Field(None, description="轉換公式")
    read_time: str = Field(..., description="讀取時間")
    range_valid: Optional[bool] = Field(None, description="範圍驗證是否通過")
    range_message: Optional[str] = Field(None, description="範圍驗證訊息")
    min_value: Optional[float] = Field(None, description="最小值")
    max_value: Optional[float] = Field(None, description="最大值")

class ModbusPointValueResponse(BaseModel):
    name: str = Field(..., description="點位名稱")
    value: Union[bool, int, float, List, None] = Field(..., description="最終數值")

class ModbusControllerValuesResponse(BaseModel):
    total: int = Field(..., description="總點位數")
    successful: int = Field(..., description="成功讀取數")
    failed: int = Field(..., description="失敗數")
    values: List[ModbusPointValueResponse] = Field(..., description="點位數值列表")

class ModbusPointWriteRequest(BaseModel):
    value: Union[bool, int, float] = Field(..., description="要寫入的數值")
    unit_id: Optional[int] = Field(1, description="單元 ID", example=1)

class ModbusPointWriteResponse(BaseModel):
    point_id: str = Field(..., description="點位 ID")
    point_name: str = Field(..., description="點位名稱")
    controller_name: str = Field(..., description="控制器名稱")
    write_value: Union[bool, int, float] = Field(..., description="寫入的數值")
    raw_data: List[Union[bool, int]] = Field(..., description="原始寫入資料")
    write_time: str = Field(..., description="寫入時間")
    success: bool = Field(..., description="寫入是否成功")

class ModbusConfigValidationResponse(BaseModel):
    is_valid: bool = Field(..., description="是否有效")
    errors: List[str] = Field(..., description="錯誤訊息列表")
    warnings: List[str] = Field(..., description="警告訊息列表")

class ModbusConfigImportResponse(BaseModel):
    imported_controllers: List[str] = Field(..., description="已匯入的控制器 ID 列表")
    total_points: int = Field(..., description="總點位數")
    import_time: str = Field(..., description="匯入時間")

modbus_controller_response_example = {
    "code": 200,
    "message": "Controller created successfully",
    "data": {
        "id": "uuid-controller-id",
        "name": "Test",
        "host": "192.168.1.100",
        "port": 502,
        "timeout": 10,
        "status": True,
        "created_at": "2024-01-01T10:00:00+00:00",
        "updated_at": "2024-01-01T10:00:00+00:00"
    }
}

modbus_controller_list_response_example = {
    "code": 200,
    "message": "Get controller list successfully",
    "data": {
        "total": 2,
        "controllers": [
            {
                "id": "uuid-controller-id-1",
                "name": "Test Controller 1",
                "host": "192.168.1.100",
                "port": 502,
                "timeout": 10,
                "status": True,
                "created_at": "2024-01-01T10:00:00+00:00",
                "updated_at": "2024-01-01T10:00:00+00:00"
            },
            {
                "id": "uuid-controller-id-2",
                "name": "Test Controller 2",
                "host": "192.168.1.101",
                "port": 502,
                "timeout": 5,
                "status": False,
                "created_at": "2024-01-01T11:00:00+00:00",
                "updated_at": "2024-01-01T11:00:00+00:00"
            }
        ]
    }
}

modbus_point_response_example = {
    "code": 200,
    "message": "Point created successfully",
    "data": {
        "id": "uuid-point-id",
        "controller_id": "uuid-controller-id",
        "name": "Temperature 1",
        "description": "Boiler temperature sensor",
        "type": "holding_register",
        "data_type": "uint16",
        "address": 0,
        "len": 1,
        "unit_id": 1,
        "formula": "x * 0.1",
        "unit": "°C",
        "min_value": 0.0,
        "max_value": 100.0,
        "created_at": "2024-01-01T10:00:00+00:00",
        "updated_at": "2024-01-01T10:00:00+00:00"
    }
}

modbus_point_list_response_example = {
    "code": 200,
    "message": "Get point list successfully",
    "data": {
        "total": 2,
        "points": [
            {
                "id": "uuid-point-id-1",
                "controller_id": "uuid-controller-id",
                "name": "Temperature 1",
                "description": "Boiler temperature sensor",
                "type": "holding_register",
                "data_type": "uint16",
                "address": 0,
                "len": 1,
                "unit_id": 1,
                "formula": "x * 0.1",
                "unit": "°C",
                "min_value": 0.0,
                "max_value": 100.0,
                "created_at": "2024-01-01T10:00:00+00:00",
                "updated_at": "2024-01-01T10:00:00+00:00"
            },
            {
                "id": "uuid-point-id-2",
                "controller_id": "uuid-controller-id",
                "name": "Pressure 1",
                "description": "System pressure",
                "type": "input_register",
                "data_type": "uint16",
                "address": 1,
                "len": 1,
                "unit_id": 1,
                "formula": None,
                "unit": "bar",
                "min_value": 0.0,
                "max_value": 10.0,
                "created_at": "2024-01-01T10:05:00+00:00",
                "updated_at": "2024-01-01T10:05:00+00:00"
            }
        ]
    }
}

modbus_multi_point_data_response_example = {
    "code": 200,
    "message": "Controller values read successfully",
    "data": {
        "total": 2,
        "successful": 2,
        "failed": 0,
        "values": [
            {
                "name": "Temperature 1",
                "value": 205.0
            },
            {
                "name": "Pressure 1",
                "value": 150
            }
        ]
    }
}

modbus_point_write_response_example = {
    "code": 200,
    "message": "Point data written successfully",
    "data": {
        "point_id": "uuid-point-id",
        "point_name": "Setpoint 1",
        "controller_name": "Test Controller",
        "write_value": 75.0,
        "raw_data": [750],
        "write_time": "2024-01-01T10:00:00+00:00",
        "success": True
    }
}

modbus_config_import_response_example = {
    "code": 200,
    "message": "Configuration imported successfully",
    "data": {
        "imported_controllers": ["uuid-controller-id-1", "uuid-controller-id-2"],
        "total_points": 15,
        "import_time": "2024-01-01T10:00:00+00:00"
    }
}

modbus_config_validation_response_example = {
    "code": 200,
    "message": "Configuration validation completed",
    "data": {
        "is_valid": True,
        "errors": [],
        "warnings": ["Some optional fields are missing"]
    }
}