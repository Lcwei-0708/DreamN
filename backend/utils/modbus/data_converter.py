import logging
from enum import Enum
from datetime import datetime
from models.modbus_point import ModbusPoint
from typing import Dict, List, Any, Optional
from models.modbus_controller import ModbusController

logger = logging.getLogger(__name__)

class ModbusDataType(str, Enum):
    """Modbus data types"""
    BOOL = "bool"
    INT16 = "int16"
    UINT16 = "uint16"
    INT32 = "int32"
    UINT32 = "uint32"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    STRING = "string"

class ModbusPointType(str, Enum):
    """Modbus point types"""
    COIL = "coil"
    INPUT = "input"
    HOLDING_REGISTER = "holding_register"
    INPUT_REGISTER = "input_register"

class ModbusFunctionCode(int, Enum):
    """Modbus function codes"""
    READ_COILS = 1
    READ_DISCRETE_INPUTS = 2
    READ_HOLDING_REGISTERS = 3
    READ_INPUT_REGISTERS = 4
    WRITE_SINGLE_COIL = 5
    WRITE_SINGLE_REGISTER = 6
    WRITE_MULTIPLE_COILS = 15
    WRITE_MULTIPLE_REGISTERS = 16

class ModbusDataConverter:
    """Handle data format conversions between different Modbus formats"""
    
    # Function code to point type mapping
    FUNCTION_CODE_TO_TYPE = {
        ModbusFunctionCode.READ_COILS: ModbusPointType.COIL,
        ModbusFunctionCode.READ_DISCRETE_INPUTS: ModbusPointType.INPUT,
        ModbusFunctionCode.READ_HOLDING_REGISTERS: ModbusPointType.HOLDING_REGISTER,
        ModbusFunctionCode.READ_INPUT_REGISTERS: ModbusPointType.INPUT_REGISTER,
        ModbusFunctionCode.WRITE_SINGLE_COIL: ModbusPointType.COIL,
        ModbusFunctionCode.WRITE_SINGLE_REGISTER: ModbusPointType.HOLDING_REGISTER,
        ModbusFunctionCode.WRITE_MULTIPLE_COILS: ModbusPointType.COIL,
        ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS: ModbusPointType.HOLDING_REGISTER,
    }
    
    # Point type to function code mapping
    TYPE_TO_FUNCTION_CODE = {
        ModbusPointType.COIL: {
            "read": ModbusFunctionCode.READ_COILS,
            "write": ModbusFunctionCode.WRITE_SINGLE_COIL
        },
        ModbusPointType.INPUT: {
            "read": ModbusFunctionCode.READ_DISCRETE_INPUTS,
            "write": None
        },
        ModbusPointType.HOLDING_REGISTER: {
            "read": ModbusFunctionCode.READ_HOLDING_REGISTERS,
            "write": ModbusFunctionCode.WRITE_SINGLE_REGISTER
        },
        ModbusPointType.INPUT_REGISTER: {
            "read": ModbusFunctionCode.READ_INPUT_REGISTERS,
            "write": None
        }
    }
    
    # ThingsBoard data type to system data type mapping
    TB_TYPE_TO_DATA_TYPE = {
        "bits": ModbusDataType.BOOL,
        "bytes": ModbusDataType.UINT16,
        "int16": ModbusDataType.INT16,
        "uint16": ModbusDataType.UINT16,
        "int32": ModbusDataType.INT32,
        "uint32": ModbusDataType.UINT32,
        "float32": ModbusDataType.FLOAT32,
        "float64": ModbusDataType.FLOAT64,
        "string": ModbusDataType.STRING,
    }
    
    # System data type to ThingsBoard type mapping
    DATA_TYPE_TO_TB_TYPE = {
        ModbusDataType.BOOL: "bits",
        ModbusDataType.INT16: "int16",
        ModbusDataType.UINT16: "uint16",
        ModbusDataType.INT32: "int32",
        ModbusDataType.UINT32: "uint32",
        ModbusDataType.FLOAT32: "float32",
        ModbusDataType.FLOAT64: "float64",
        ModbusDataType.STRING: "string",
    }
    
    @classmethod
    def convert_thingsboard_to_unified_format(cls, slave: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert ThingsBoard format to unified internal format"""
        points_data = []
        unit_id = slave.get("unitId", 1)
        
        # Collect all points from different sections and deduplicate by address, unit_id, and type
        all_points = {}
        
        # Process attributes (coils and discrete inputs)
        for attr in slave.get("attributes", []):
            point_key = cls._create_point_key(attr, unit_id)
            if point_key not in all_points:
                all_points[point_key] = {
                    "data": attr,
                    "sections": ["attribute"],
                    "items": [attr]
                }
            else:
                all_points[point_key]["sections"].append("attribute")
                all_points[point_key]["items"].append(attr)
        
        # Process timeseries (holding registers and input registers)
        for ts in slave.get("timeseries", []):
            point_key = cls._create_point_key(ts, unit_id)
            if point_key not in all_points:
                all_points[point_key] = {
                    "data": ts,
                    "sections": ["timeseries"],
                    "items": [ts]
                }
            else:
                all_points[point_key]["sections"].append("timeseries")
                all_points[point_key]["items"].append(ts)
        
        # Process RPC (writable points)
        for rpc in slave.get("rpc", []):
            point_key = cls._create_point_key(rpc, unit_id)
            if point_key not in all_points:
                all_points[point_key] = {
                    "data": rpc,
                    "sections": ["rpc"],
                    "items": [rpc]
                }
            else:
                all_points[point_key]["sections"].append("rpc")
                all_points[point_key]["items"].append(rpc)
        
        # Convert each unique point
        for point_key, point_info in all_points.items():
            point_data = cls._convert_thingsboard_item_merged(point_info, unit_id)
            if point_data:
                points_data.append(point_data)
        
        return points_data

    @classmethod
    def _create_point_key(cls, item: Dict[str, Any], unit_id: int) -> str:
        """Create a unique key for a point based on address, unit_id, and type"""
        function_code = item.get("functionCode")
        point_type = cls._get_point_type_from_function_code(function_code)
        address = item.get("address", 0)
        
        # For holding registers, both read (function code 3) and write (function code 6) 
        # should be merged into the same point
        if point_type == ModbusPointType.HOLDING_REGISTER:
            point_type = ModbusPointType.HOLDING_REGISTER
        
        return f"{address}_{unit_id}_{point_type}"

    @classmethod
    def _convert_thingsboard_item_merged(cls, point_info: Dict[str, Any], unit_id: int) -> Optional[Dict[str, Any]]:
        """Convert merged ThingsBoard items to unified format"""
        try:
            items = point_info["items"]
            sections = point_info["sections"]
            
            # Use the first item as base for common properties
            base_item = items[0]
            function_code = base_item.get("functionCode")
            point_type = cls._get_point_type_from_function_code(function_code)
            
            if not point_type:
                logger.warning(f"Unsupported function code {function_code} for item {base_item.get('tag', 'unknown')}")
                return None
            
            # Determine the best name for the merged point
            # Prefer timeseries name, then rpc name, then attribute name
            name = base_item.get("tag", "Imported Point")
            for item in items:
                if "timeseries" in sections and item.get("tag"):
                    name = item.get("tag")
                    break
                elif "rpc" in sections and item.get("tag"):
                    name = item.get("tag")
                    break
            
            # Determine data type from all items (prefer more specific types)
            data_type = ModbusDataType.UINT16  # default
            for item in items:
                item_type = cls.TB_TYPE_TO_DATA_TYPE.get(item.get("type", "uint16"), ModbusDataType.UINT16)
                # Prefer more specific types (e.g., float32 over uint16)
                if item_type in [ModbusDataType.FLOAT32, ModbusDataType.FLOAT64, ModbusDataType.INT32, ModbusDataType.UINT32]:
                    data_type = item_type
                    break
                elif item_type in [ModbusDataType.INT16, ModbusDataType.UINT16] and data_type == ModbusDataType.UINT16:
                    data_type = item_type
            
            # Determine length from all items (use maximum length)
            max_len = 1
            for item in items:
                item_len = item.get("objectsCount", 1)
                max_len = max(max_len, item_len)
            
            return {
                "name": name,
                "type": point_type,
                "data_type": data_type,
                "address": base_item.get("address", 0),
                "len": max_len,
                "unit_id": unit_id,
                "description": None,
                "formula": None,
                "unit": None,
                "min_value": None,
                "max_value": None,
                "sections": "+".join(sections),
                "merged_items": len(items)
            }
        except Exception as e:
            logger.error(f"Error converting merged ThingsBoard items: {e}")
            return None
    
    @classmethod
    def _get_point_type_from_function_code(cls, function_code: int) -> Optional[str]:
        """Get point type from function code"""
        return cls.FUNCTION_CODE_TO_TYPE.get(function_code, None)
    
    @classmethod
    def convert_points_to_thingsboard_format(cls, controller: ModbusController, points: List[ModbusPoint]) -> Dict[str, Any]:
        """Convert points to ThingsBoard format"""
        # Group points by unit_id
        points_by_unit = {}
        for point in points:
            unit_id = point.unit_id
            if unit_id not in points_by_unit:
                points_by_unit[unit_id] = []
            points_by_unit[unit_id].append(point)
        
        slaves = []
        for unit_id, unit_points in points_by_unit.items():
            slave = cls._create_thingsboard_slave_config(controller, unit_id)
            cls._add_points_to_thingsboard_slave(slave, unit_points)
            slaves.append(slave)
        
        return {
            "master": {"slaves": slaves},
            "export_time": datetime.now().isoformat(),
            "format": "thingsboard"
        }
    
    @classmethod
    def _create_thingsboard_slave_config(cls, controller: ModbusController, unit_id: int) -> Dict[str, Any]:
        """Create ThingsBoard slave configuration"""
        return {
            "method": "socket",
            "type": "tcp",
            "host": controller.host,
            "port": controller.port,
            "timeout": controller.timeout,
            "retries": 3,
            "pollPeriod": 1000,
            "unitId": unit_id,
            "deviceName": controller.name,
            "deviceType": controller.name.lower().replace(" ", "_"),
            "attributes": [],
            "timeseries": [],
            "rpc": []
        }
    
    @classmethod
    def _add_points_to_thingsboard_slave(cls, slave: Dict[str, Any], points: List[ModbusPoint]):
        """Add points to ThingsBoard slave configuration"""
        for point in points:
            tb_type = "bytes"
            read_function_code = cls.TYPE_TO_FUNCTION_CODE[point.type]["read"]
            write_function_code = cls.TYPE_TO_FUNCTION_CODE[point.type]["write"]
            
            point_config = {
                "tag": point.name,
                "type": tb_type,
                "functionCode": read_function_code,
                "objectsCount": point.len,
                "address": point.address
            }
            
            # Determine which section to place based on point type
            if point.type in [ModbusPointType.COIL, ModbusPointType.INPUT]:
                slave["attributes"].append(point_config)
            elif point.type in [ModbusPointType.HOLDING_REGISTER, ModbusPointType.INPUT_REGISTER]:
                slave["timeseries"].append(point_config)
            
            # Add RPC configuration for writable points
            if write_function_code:
                rpc_config = {
                    "tag": f"set_{point.name}",
                    "type": tb_type,
                    "functionCode": write_function_code,
                    "address": point.address
                }
                if point.type == ModbusPointType.HOLDING_REGISTER:
                    rpc_config["objectsCount"] = point.len
                slave["rpc"].append(rpc_config)
    
    @classmethod
    def calculate_total_points_from_thingsboard(cls, slave: Dict[str, Any]) -> int:
        """Calculate total unique points from ThingsBoard slave configuration"""
        all_point_tags = set()
        for attr in slave.get("attributes", []):
            all_point_tags.add(attr.get("tag"))
        for ts in slave.get("timeseries", []):
            all_point_tags.add(ts.get("tag"))
        for rpc in slave.get("rpc", []):
            all_point_tags.add(rpc.get("tag"))
        return len(all_point_tags)