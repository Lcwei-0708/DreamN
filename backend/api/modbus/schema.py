from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Union

class PointType(str, Enum):
    coil = "coil"
    input = "input"
    holding_register = "holding_register"
    input_register = "input_register"

class ConfigFormat(str, Enum):
    """Configuration file format"""
    native = "native"
    thingsboard = "thingsboard"

class BatchDeleteResult(BaseModel):
    id: str = Field(..., description="項目 ID")
    status: str = Field(..., description="操作狀態(success: 成功, not_found: 找不到, error: 錯誤)", example="success|not_found|error")
    message: str = Field(..., description="狀態訊息")

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
    
    class Config:
        from_attributes = True

class ModbusControllerListResponse(BaseModel):
    total: int = Field(..., description="總數量")
    controllers: List[ModbusControllerResponse] = Field(..., description="控制器列表")

class ModbusControllerDeleteRequest(BaseModel):
    controller_ids: List[str] = Field(..., min_length=1, description="要刪除的控制器 ID 列表")

class ModbusControllerDeleteResponse(BaseModel):
    total_requested: int = Field(..., description="請求的總控制器數")
    deleted_count: int = Field(..., description="成功刪除的控制器數")
    failed_count: int = Field(..., description="刪除失敗的控制器數")
    results: List[BatchDeleteResult] = Field(..., description="每個控制器的刪除結果")

class ModbusControllerDeleteFailedResponse(BaseModel):
    results: List[BatchDeleteResult] = Field(..., description="每個控制器的刪除失敗結果")

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
    points: List[ModbusPointCreateRequest] = Field(..., description="要建立的點位列表")

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
    
    class Config:
        from_attributes = True

class ModbusPointListResponse(BaseModel):
    total: int = Field(..., description="總數量")
    points: List[ModbusPointResponse] = Field(..., description="點位列表")

class ModbusPointDeleteRequest(BaseModel):
    point_ids: List[str] = Field(..., min_length=1, description="要刪除的點位 ID 列表")

class ModbusPointDeleteResponse(BaseModel):
    total_requested: int = Field(..., description="請求的總點位數")
    deleted_count: int = Field(..., description="成功刪除的點位數")
    failed_count: int = Field(..., description="刪除失敗的點位數")
    results: List[BatchDeleteResult] = Field(..., description="每個點位的刪除結果")

class ModbusPointDeleteFailedResponse(BaseModel):
    results: List[BatchDeleteResult] = Field(..., description="每個點位的刪除失敗結果")

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
    point_id: str = Field(..., description="點位 ID")
    point_name: str = Field(..., description="點位名稱")
    value: Union[bool, int, float, List, None] = Field(..., description="最終數值")
    unit: Optional[str] = Field(None, description="單位")
    timestamp: str = Field(..., description="讀取時間")

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

class ModbusControllerValidationInfo(BaseModel):
    controller_name: str = Field(..., description="控制器名稱")
    points_count: int = Field(..., description="該控制器的點位數量")

class ModbusPointBatchCreateResult(BaseModel):
    point_id: Optional[str] = Field(None, description="點位 ID")
    name: str = Field(..., description="點位名稱")
    status: str = Field(..., description="操作狀態(success: 成功, skipped: 跳過, invalid: 無效, error: 錯誤)", example="success|skipped|invalid|error")
    message: str = Field(..., description="狀態訊息")

class ModbusPointBatchCreateResponseInternal(BaseModel):
    results: List[ModbusPointBatchCreateResult] = Field(..., description="每個點位的建立結果")
    total_requested: Optional[int] = Field(None, description="請求的總點位數")
    success_count: Optional[int] = Field(None, description="成功建立的點位數")
    skipped_count: Optional[int] = Field(None, description="被跳過的點位數")
    failed_count: Optional[int] = Field(None, description="建立失敗的點位數")

class ModbusPointBatchCreateResponse(BaseModel):
    results: List[ModbusPointBatchCreateResult] = Field(..., description="每個點位的建立結果")
    total_requested: Optional[int] = Field(None, description="請求的總點位數")

def create_modbus_point_batch_response(internal_response: ModbusPointBatchCreateResponseInternal) -> ModbusPointBatchCreateResponse:
    """Create modbus point batch response"""
    return ModbusPointBatchCreateResponse(
        results=internal_response.results,
        total_requested=internal_response.total_requested
    )

class ModbusPointImportResult(BaseModel):
    point_id: Optional[str] = Field(None, description="點位 ID")
    point_name: str = Field(..., description="點位名稱")
    status: str = Field(..., description="操作狀態(success: 成功, skipped: 跳過, failed: 失敗)")
    message: str = Field(..., description="狀態訊息")

class ModbusConfigImportResponseInternal(BaseModel):
    controller_id: Optional[str] = Field(None, description="控制器 ID")
    controller_name: str = Field(..., description="控制器名稱")
    points: List[ModbusPointImportResult] = Field(..., description="點位匯入結果")
    total_points: int = Field(..., description="總點位數")
    success_count: Optional[int] = Field(None, description="成功點位數")
    skipped_count: Optional[int] = Field(None, description="跳過點位數")
    failed_count: Optional[int] = Field(None, description="失敗點位數")

class ModbusConfigImportResponse(BaseModel):
    controller_id: Optional[str] = Field(None, description="控制器 ID")
    controller_name: str = Field(..., description="控制器名稱")
    points: List[ModbusPointImportResult] = Field(..., description="點位匯入結果")
    total_points: int = Field(..., description="總點位數")

def create_modbus_config_import_response(internal_response: ModbusConfigImportResponseInternal) -> ModbusConfigImportResponse:
    """Create modbus config import response"""
    return ModbusConfigImportResponse(
        controller_id=internal_response.controller_id,
        controller_name=internal_response.controller_name,
        points=internal_response.points,
        total_points=internal_response.total_points
    )

class ImportMode(str, Enum):
    """Import mode for handling duplicate controllers and points"""
    SKIP_CONTROLLER = "skip_controller"  # Skip entire controller if it exists
    OVERWRITE_CONTROLLER = "overwrite_controller"  # Overwrite entire controller and all points
    SKIP_DUPLICATES_POINT = "skip_duplicates_point"  # Keep controller, skip duplicate points
    OVERWRITE_DUPLICATES_POINT = "overwrite_duplicates_point"  # Keep controller, overwrite duplicate points

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
                "point_id": "uuid-point-id-1",
                "name": "Temperature 1",
                "value": 205.0
            },
            {
                "point_id": "uuid-point-id-2",
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

modbus_controller_delete_response_example = {
    "code": 207,
    "message": "Delete controllers with partial success",
    "data": {
        "total_requested": 4,
        "deleted_count": 1,
        "failed_count": 3,
        "results": [
            {"id": "uuid-controller-id-1", "status": "success", "message": "Deleted Successfully"},
            {"id": "uuid-controller-id-2", "status": "not_found", "message": "Controller not found"},
            {"id": "uuid-controller-id-3", "status": "error", "message": "Server error"}
        ]
    }
}

modbus_point_delete_response_example = {
    "code": 207,
    "message": "Delete points with partial success",
    "data": {
        "total_requested": 4,
        "deleted_count": 1,
        "failed_count": 3,
        "results": [
            {"id": "uuid-point-id-1", "status": "success", "message": "Deleted Successfully"},
            {"id": "uuid-point-id-2", "status": "not_found", "message": "Point not found"},
            {"id": "uuid-point-id-3", "status": "error", "message": "Server error"}
        ]
    }
}

modbus_controller_delete_failed_response_example = {
    "code": 400,
    "message": "All controllers failed to delete",
    "data": {
        "results": [
            {"id": "uuid-controller-id-1", "status": "not_found", "message": "Controller not found"},
            {"id": "uuid-controller-id-2", "status": "error", "message": "Server Error"}
        ]
    }
}

modbus_point_delete_failed_response_example = {
    "code": 400,
    "message": "All points failed to delete",
    "data": {
        "results": [
            {"id": "uuid-point-id-1", "status": "not_found", "message": "Not found"},
            {"id": "uuid-point-id-2", "status": "error", "message": "Server error"}
        ]
    }
}

modbus_point_batch_create_simple_response_example = {
    "code": 200,
    "message": "All points created successfully",
    "data": {
        "results": [
            {
                "point_id": "uuid-point-id-1",
                "name": "Temperature 1",
                "status": "success",
                "message": "Created successfully"
            },
            {
                "point_id": "uuid-point-id-2",
                "name": "Pressure 1",
                "status": "success",
                "message": "Created successfully"
            }
        ],
        "total_requested": 2
    }
}

modbus_point_batch_create_partial_response_example = {
    "code": 207,
    "message": "Points created with partial success",
    "data": {
        "results": [
            {
                "point_id": "uuid-point-id-1",
                "name": "Temperature 1",
                "status": "success",
                "message": "Created successfully"
            },
            {
                "point_id": None,
                "name": "Temperature 2",
                "status": "skipped",
                "message": "Point already exists"
            },
            {
                "point_id": None,
                "name": "Temperature 3",
                "status": "invalid",
                "message": "Invalid point"
            }
        ],
        "total_requested": 3,
        "success_count": 1,
        "skipped_count": 1,
        "failed_count": 1
    }
}

modbus_point_batch_create_failed_response_example = {
    "code": 400,
    "message": "All points failed to create",
    "data": {
        "results": [
            {
                "point_id": None,
                "name": "Temperature 1",
                "status": "skipped",
                "message": "Point already exists"
            },
            {
                "point_id": None,
                "name": "Temperature 2",
                "status": "invalid",
                "message": "Invalid point"
            }
        ],
        "total_requested": 2,
        "skipped_count": 1,
        "failed_count": 1
    }
}

modbus_config_import_simple_response_example = {
    "code": 200,
    "message": "Controller imported successfully",
    "data": {
        "controller_id": "uuid-controller-id-1",
        "controller_name": "Controller 1",
        "points": [
            {
                "point_id": "uuid-point-id-1",
                "point_name": "Temperature 1",
                "status": "success",
                "message": "Imported successfully"
            },
        ],
        "total_points": 1
    }
}

modbus_config_import_partial_response_example = {
    "code": 207,
    "message": "Controller imported with partial success",
    "data": {
        "controller_id": "uuid-controller-id-1",
        "controller_name": "Controller 1",
        "points": [
            {
                "point_id": "uuid-point-id-1",
                "point_name": "Temperature 1",
                "status": "success",
                "message": "Imported successfully"
            },
            {
                "point_name": "Pressure 1",
                "status": "skipped",
                "message": "Point already exists"
            },
            {
                "point_name": "Pressure 2",
                "status": "invalid",
                "message": "Invalid point"
            }
        ],
        "total_points": 3,
        "success_count": 1,
        "skipped_count": 1,
        "failed_count": 1
    }
}

modbus_config_import_failed_response_example = {
    "code": 400,
    "message": "All points failed to import",
    "data": {
        "controller_name": "Controller 1",
        "points": [
            {
                "point_name": "Temperature 1",
                "status": "error",
                "message": "Point error"
            },
            {
                "point_name": "Temperature 2",
                "status": "invalid",
                "message": "Invalid point"
            }
        ],
        "total_points": 2,
        "skipped_count": 0,
        "failed_count": 2
    }
}