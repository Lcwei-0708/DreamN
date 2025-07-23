"""
Modbus Configuration Import/Export Manager

This module provides functionality to export Modbus controller and point configurations
to different formats (native, thingsboard) and import configurations from these formats.
"""

import logging
from enum import Enum
from datetime import datetime
from sqlalchemy import select, delete, update
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models.modbus_point import ModbusPoint
from models.modbus_controller import ModbusController
from utils.custom_exception import ModbusConfigException, ModbusConfigFormatMismatchException, ModbusControllerDuplicateException, ModbusPointDuplicateException

logger = logging.getLogger(__name__)

class ConfigFormat(str, Enum):
    """Supported configuration formats"""
    NATIVE = "native"
    THINGSBOARD = "thingsboard"


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


class ModbusPointType(str, Enum):
    """Modbus point types"""
    COIL = "coil"
    INPUT = "input"
    HOLDING_REGISTER = "holding_register"
    INPUT_REGISTER = "input_register"


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


@dataclass
class ModbusConfigValidationResult:
    """Configuration validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ModbusConfigManager:
    """Modbus Configuration Manager for import/export operations"""
    
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
    
    def __init__(self):
        self.default_values = {
            "timeout": 10,
            "retries": 3,
            "poll_period": 1000,
            "len": 1,
            "unit_id": 1,
            "formula": None,
            "unit": None,
            "min_value": None,
            "max_value": None,
            "description": None,
        }
    
    async def export_config(
        self, 
        controller_ids: List[str] = None, 
        db: AsyncSession = None, 
        format: ConfigFormat = ConfigFormat.NATIVE
    ) -> Dict[str, Any]:
        """
        Export Modbus configuration for specified controllers or all controllers
        
        Args:
            controller_ids: List of controller IDs to export (None = export all)
            db: Database session
            format: Export format (native or thingsboard)
            
        Returns:
            Configuration dictionary in the specified format
        """
        try:
            if db is None:
                raise ModbusConfigException("Database session (db) is required for export.")

            if controller_ids is None:
                # Export all controllers
                result = await db.execute(select(ModbusController))
                controllers = result.scalars().all()
            else:
                # Export specified controllers
                controllers = []
                for controller_id in controller_ids:
                    controller = await self._get_controller(controller_id, db)
                    controllers.append(controller)
            
            if not controllers:
                raise ModbusConfigException("No controllers found to export")
            
            if format == ConfigFormat.NATIVE:
                return await self._export_native_format_multi(controllers, db)
            elif format == ConfigFormat.THINGSBOARD:
                return await self._export_thingsboard_format_multi(controllers, db)
            else:
                raise ModbusConfigException(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            raise ModbusConfigException(f"Export failed: {str(e)}")
    
    async def import_config(
        self, 
        config: Dict[str, Any], 
        db: AsyncSession, 
        format: ConfigFormat = ConfigFormat.NATIVE,
        overwrite: bool = False
    ) -> List[ModbusController]:
        """
        Import Modbus configuration from the specified format
        
        Args:
            config: Configuration dictionary
            db: Database session
            format: Import format (native or thingsboard)
            overwrite: Whether to overwrite existing controllers and points
            
        Returns:
            List of created controllers
        """
        try:
            validation_result = self._validate_config(config, format)
            if not validation_result.is_valid:
                raise ModbusConfigException(f"Invalid configuration: {validation_result.errors}")
            
            if format == ConfigFormat.NATIVE:
                return await self._import_native_format(config, db, overwrite)
            elif format == ConfigFormat.THINGSBOARD:
                return await self._import_thingsboard_format(config, db, overwrite)
            else:
                raise ModbusConfigException(f"Unsupported format: {format}")
                
        except (ModbusConfigFormatMismatchException, ModbusControllerDuplicateException):
            raise
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            raise ModbusConfigException(f"Import failed: {str(e)}")
    
    def validate_config(self, config: Dict[str, Any], format: ConfigFormat) -> ModbusConfigValidationResult:
        """
        Validate configuration format and content
        
        Args:
            config: Configuration dictionary
            format: Expected format
            
        Returns:
            Validation result with errors and warnings
        """
        return self._validate_config(config, format)
    
    def _export_native_format(self, controller: ModbusController, points: List[ModbusPoint]) -> Dict[str, Any]:
        """Export in native format"""
        return {
            "format": "native",
            "export_time": datetime.now().isoformat(),
            "controller": {
                "name": controller.name,
                "host": controller.host,
                "port": controller.port,
                "timeout": controller.timeout,
            },
            "points": [
                {
                    "name": point.name,
                    "description": point.description,
                    "type": point.type,
                    "data_type": point.data_type,
                    "address": point.address,
                    "len": point.len,
                    "unit_id": point.unit_id,
                    "formula": point.formula,
                    "unit": point.unit,
                    "min_value": point.min_value,
                    "max_value": point.max_value,
                }
                for point in points
            ]
        }
    
    def _export_thingsboard_format(self, controller: ModbusController, points: List[ModbusPoint]) -> Dict[str, Any]:
        """Export in ThingsBoard format"""
        # Group points by unit_id
        points_by_unit = {}
        for point in points:
            unit_id = point.unit_id
            if unit_id not in points_by_unit:
                points_by_unit[unit_id] = []
            points_by_unit[unit_id].append(point)
        
        slaves = []
        for unit_id, unit_points in points_by_unit.items():
            slave = {
                "method": "socket",
                "type": "tcp",
                "host": controller.host,
                "port": controller.port,
                "timeout": controller.timeout,
                "retries": self.default_values["retries"],
                "pollPeriod": self.default_values["poll_period"],
                "unitId": unit_id,
                "deviceName": f"{controller.name}",
                "deviceType": controller.name.lower().replace(" ", "_"),
                "attributes": [],
                "timeseries": [],
                "rpc": []
            }
            
            for point in unit_points:
                tb_type = "bytes"
                read_function_code = self.TYPE_TO_FUNCTION_CODE[point.type]["read"]
                write_function_code = self.TYPE_TO_FUNCTION_CODE[point.type]["write"]
                
                # Determine which section to place based on point type
                if point.type in [ModbusPointType.COIL, ModbusPointType.INPUT]:
                    # Coils and discrete inputs go in attributes
                    point_config = {
                        "tag": point.name,
                        "type": tb_type,
                        "functionCode": read_function_code,
                        "objectsCount": point.len,
                        "address": point.address
                    }
                    slave["attributes"].append(point_config)
                    
                    # If it's a coil and supports writing, add RPC
                    if point.type == ModbusPointType.COIL and write_function_code:
                        rpc_config = {
                            "tag": f"set_{point.name}",
                            "type": tb_type,
                            "functionCode": write_function_code,
                            "address": point.address
                        }
                        slave["rpc"].append(rpc_config)
                        
                elif point.type in [ModbusPointType.HOLDING_REGISTER, ModbusPointType.INPUT_REGISTER]:
                    # Holding registers and input registers go in timeseries
                    point_config = {
                        "tag": point.name,
                        "type": tb_type,
                        "functionCode": read_function_code,
                        "objectsCount": point.len,
                        "address": point.address
                    }
                    slave["timeseries"].append(point_config)
                    
                    # If it's a holding register and supports writing, add RPC
                    if point.type == ModbusPointType.HOLDING_REGISTER and write_function_code:
                        rpc_config = {
                            "tag": f"set_{point.name}",
                            "type": tb_type,
                            "functionCode": write_function_code,
                            "address": point.address,
                            "objectsCount": point.len
                        }
                        slave["rpc"].append(rpc_config)
            
            slaves.append(slave)
        
        return {
            "master": {
                "slaves": slaves
            },
            "export_time": datetime.now().isoformat(),
            "format": "thingsboard"
        }
    
    async def _export_native_format_multi(self, controllers: List[ModbusController], db: AsyncSession) -> Dict[str, Any]:
        """Export multiple controllers in native format"""
        all_controllers_data = []
        
        for controller in controllers:
            # Get points for this controller
            points_result = await db.execute(
                select(ModbusPoint).where(ModbusPoint.controller_id == controller.id)
            )
            points = points_result.scalars().all()
            
            controller_data = {
                "name": controller.name,
                "host": controller.host,
                "port": controller.port,
                "timeout": controller.timeout,
                "points": [
                    {
                        "name": point.name,
                        "description": point.description,
                        "type": point.type,
                        "data_type": point.data_type,
                        "address": point.address,
                        "len": point.len,
                        "unit_id": point.unit_id,
                        "formula": point.formula,
                        "unit": point.unit,
                        "min_value": point.min_value,
                        "max_value": point.max_value,
                    }
                    for point in points
                ]
            }
            all_controllers_data.append(controller_data)
        
        return {
            "format": "native",
            "export_time": datetime.now().isoformat(),
            "controllers": all_controllers_data
        }

    async def _export_thingsboard_format_multi(self, controllers: List[ModbusController], db: AsyncSession) -> Dict[str, Any]:
        """Export multiple controllers in ThingsBoard format"""
        all_slaves = []
        
        for controller in controllers:
            # Get points for this controller
            points_result = await db.execute(
                select(ModbusPoint).where(ModbusPoint.controller_id == controller.id)
            )
            points = points_result.scalars().all()
            
            # Group points by unit_id
            points_by_unit = {}
            for point in points:
                unit_id = point.unit_id
                if unit_id not in points_by_unit:
                    points_by_unit[unit_id] = []
                points_by_unit[unit_id].append(point)
            
            for unit_id, unit_points in points_by_unit.items():
                slave = {
                    "method": "socket",
                    "type": "tcp",
                    "host": controller.host,
                    "port": controller.port,
                    "timeout": controller.timeout,
                    "retries": self.default_values["retries"],
                    "pollPeriod": self.default_values["poll_period"],
                    "unitId": unit_id,
                    "deviceName": f"{controller.name}",
                    "deviceType": controller.name.lower().replace(" ", "_"),
                    "attributes": [],
                    "timeseries": [],
                    "rpc": []
                }
                
                for point in unit_points:
                    tb_type = "bytes"
                    read_function_code = self.TYPE_TO_FUNCTION_CODE[point.type]["read"]
                    write_function_code = self.TYPE_TO_FUNCTION_CODE[point.type]["write"]
                    
                    # Determine which section to place based on point type
                    if point.type in [ModbusPointType.COIL, ModbusPointType.INPUT]:
                        # Coils and discrete inputs go in attributes
                        point_config = {
                            "tag": point.name,
                            "type": tb_type,
                            "functionCode": read_function_code,
                            "objectsCount": point.len,
                            "address": point.address
                        }
                        slave["attributes"].append(point_config)
                        
                        # If it's a coil and supports writing, add RPC
                        if point.type == ModbusPointType.COIL and write_function_code:
                            rpc_config = {
                                "tag": f"set_{point.name}",
                                "type": tb_type,
                                "functionCode": write_function_code,
                                "address": point.address
                            }
                            slave["rpc"].append(rpc_config)
                            
                    elif point.type in [ModbusPointType.HOLDING_REGISTER, ModbusPointType.INPUT_REGISTER]:
                        # Holding registers and input registers go in timeseries
                        point_config = {
                            "tag": point.name,
                            "type": tb_type,
                            "functionCode": read_function_code,
                            "objectsCount": point.len,
                            "address": point.address
                        }
                        slave["timeseries"].append(point_config)
                        
                        # If it's a holding register and supports writing, add RPC
                        if point.type == ModbusPointType.HOLDING_REGISTER and write_function_code:
                            rpc_config = {
                                "tag": f"set_{point.name}",
                                "type": tb_type,
                                "functionCode": write_function_code,
                                "address": point.address,
                                "objectsCount": point.len
                            }
                            slave["rpc"].append(rpc_config)
                
                all_slaves.append(slave)
        
        return {
            "master": {
                "slaves": all_slaves
            },
            "export_time": datetime.now().isoformat(),
            "format": "thingsboard"
        }
    
    async def _import_native_format(self, config: Dict[str, Any], db: AsyncSession, overwrite: bool = False) -> Dict[str, Any]:
        """Import from native format (supports both single and multiple controllers)"""
        imported_controllers = []
        skipped_controllers = []
        
        # Check if it's single controller format (backward compatibility)
        if "controller" in config and "points" in config:
            controller_data = config.get("controller", {})
            points_data = config.get("points", [])
            
            # Check for existing controller
            existing_controller = await db.execute(
                select(ModbusController).where(
                    ModbusController.host == controller_data.get("host"),
                    ModbusController.port == controller_data.get("port")
                )
            )
            existing_controller = existing_controller.scalar_one_or_none()
            
            if existing_controller:
                if overwrite:
                    # Update existing controller
                    await db.execute(
                        update(ModbusController)
                        .where(ModbusController.id == existing_controller.id)
                        .values(
                            name=controller_data.get("name"),
                            timeout=controller_data.get("timeout", 10),
                            updated_at=datetime.now()
                        )
                    )
                    
                    # Delete existing points
                    await db.execute(
                        delete(ModbusPoint).where(ModbusPoint.controller_id == existing_controller.id)
                    )
                    
                    controller = existing_controller
                    logger.info(f"Updated existing controller {existing_controller.name} ({controller_data.get('host')}:{controller_data.get('port')})")
                else:
                    # Skip duplicate controller when not overwriting
                    skipped_controllers.append({
                        "controller_name": controller_data.get("name"),
                        "host": controller_data.get("host"),
                        "port": controller_data.get("port"),
                        "reason": "Controller already exists"
                    })
                    logger.warning(f"Skipped duplicate controller {existing_controller.name} ({controller_data.get('host')}:{controller_data.get('port')})")
                    return {
                        "imported_controllers": imported_controllers,
                        "skipped_controllers": skipped_controllers,
                        "total_requested": 1,
                        "imported_count": 0,
                        "skipped_count": 1
                    }
            else:
                # Create new controller
                controller = ModbusController(
                    name=controller_data.get("name"),
                    host=controller_data.get("host"),
                    port=controller_data.get("port"),
                    timeout=controller_data.get("timeout", 10),
                    status=False
                )
                db.add(controller)
                await db.commit()
                await db.refresh(controller)
            
            # Create points
            for point_data in points_data:
                point = ModbusPoint(
                    controller_id=controller.id,
                    name=point_data.get("name"),
                    description=point_data.get("description"),
                    type=point_data.get("type"),
                    data_type=point_data.get("data_type"),
                    address=point_data.get("address"),
                    len=point_data.get("len", 1),
                    unit_id=point_data.get("unit_id", 1),
                    formula=point_data.get("formula"),
                    unit=point_data.get("unit"),
                    min_value=point_data.get("min_value"),
                    max_value=point_data.get("max_value")
                )
                db.add(point)
            
            await db.commit()
            imported_controllers.append(controller)
            
        # Multi-controller format
        elif "controllers" in config:
            for controller_data in config["controllers"]:
                # Check for existing controller
                existing_controller = await db.execute(
                    select(ModbusController).where(
                        ModbusController.host == controller_data.get("host"),
                        ModbusController.port == controller_data.get("port")
                    )
                )
                existing_controller = existing_controller.scalar_one_or_none()
                
                if existing_controller:
                    if overwrite:
                        # Update existing controller
                        await db.execute(
                            update(ModbusController)
                            .where(ModbusController.id == existing_controller.id)
                            .values(
                                name=controller_data.get("name"),
                                timeout=controller_data.get("timeout", 10),
                                updated_at=datetime.now()
                            )
                        )
                        
                        # Delete existing points
                        await db.execute(
                            delete(ModbusPoint).where(ModbusPoint.controller_id == existing_controller.id)
                        )
                        
                        controller = existing_controller
                        logger.info(f"Updated existing controller {existing_controller.name} ({controller_data.get('host')}:{controller_data.get('port')})")
                    else:
                        # Skip duplicate controller when not overwriting
                        skipped_controllers.append({
                            "controller_name": controller_data.get("name"),
                            "host": controller_data.get("host"),
                            "port": controller_data.get("port"),
                            "reason": "Controller already exists"
                        })
                        logger.warning(f"Skipped duplicate controller {existing_controller.name} ({controller_data.get('host')}:{controller_data.get('port')})")
                        continue  # Skip to next controller
                else:
                    # Create new controller
                    controller = ModbusController(
                        name=controller_data.get("name"),
                        host=controller_data.get("host"),
                        port=controller_data.get("port"),
                        timeout=controller_data.get("timeout", 10),
                        status=False
                    )
                    db.add(controller)
                    await db.commit()
                    await db.refresh(controller)
                
                # Create points
                for point_data in controller_data.get("points", []):
                    point = ModbusPoint(
                        controller_id=controller.id,
                        name=point_data.get("name"),
                        description=point_data.get("description"),
                        type=point_data.get("type"),
                        data_type=point_data.get("data_type"),
                        address=point_data.get("address"),
                        len=point_data.get("len", 1),
                        unit_id=point_data.get("unit_id", 1),
                        formula=point_data.get("formula"),
                        unit=point_data.get("unit"),
                        min_value=point_data.get("min_value"),
                        max_value=point_data.get("max_value")
                    )
                    db.add(point)
                
                await db.commit()
                imported_controllers.append(controller)
        
        return {
            "imported_controllers": imported_controllers,
            "skipped_controllers": skipped_controllers,
            "total_requested": len(config.get("controllers", [])) if "controllers" in config else 1,
            "imported_count": len(imported_controllers),
            "skipped_count": len(skipped_controllers)
        }
    
    async def _import_thingsboard_format(self, config: Dict[str, Any], db: AsyncSession, overwrite: bool = False) -> List[ModbusController]:
        """Import from ThingsBoard format"""
        controllers = []
        
        master = config.get("master", {})
        slaves = master.get("slaves", [])
        
        for slave in slaves:
            host = slave.get("host", "localhost")
            port = slave.get("port", 502)
            
            # Check for existing controller
            existing_controller = await db.execute(
                select(ModbusController).where(
                    ModbusController.host == host,
                    ModbusController.port == port
                )
            )
            existing_controller = existing_controller.scalar_one_or_none()
            
            if existing_controller:
                if overwrite:
                    # Delete existing controller and all its points
                    await db.execute(
                        delete(ModbusPoint).where(ModbusPoint.controller_id == existing_controller.id)
                    )
                    await db.execute(
                        delete(ModbusController).where(ModbusController.id == existing_controller.id)
                    )
                    await db.flush()
                    logger.info(f"Overwrote existing controller {existing_controller.name} ({host}:{port})")
                else:
                    raise ModbusControllerDuplicateException(
                        f"Controller with host {host} and port {port} already exists"
                    )
            
            # Create controller for each slave
            controller = ModbusController(
                name=slave.get("deviceName", "Imported Controller"),
                host=host,
                port=port,
                timeout=slave.get("timeout", self.default_values["timeout"]),
                status=False
            )
            
            db.add(controller)
            await db.flush()
            
            unit_id = slave.get("unitId", self.default_values["unit_id"])
            
            points_map = {}
            
            # Process attributes (coils and discrete inputs)
            for attr in slave.get("attributes", []):
                address = attr.get("address", 0)
                point_type = self._get_point_type_from_function_code(attr.get("functionCode"))
                key = (point_type, address, unit_id)
                data_type = self.TB_TYPE_TO_DATA_TYPE.get(attr.get("type", "bits"), ModbusDataType.BOOL)
                
                points_map[key] = {
                    "name": attr.get("tag", "Imported Point"),
                    "description": self.default_values["description"],
                    "type": point_type,
                    "data_type": data_type,
                    "address": address,
                    "len": attr.get("objectsCount", self.default_values["len"]),
                    "unit_id": unit_id,
                    "formula": self.default_values["formula"],
                    "unit": self.default_values["unit"],
                    "min_value": self.default_values["min_value"],
                    "max_value": self.default_values["max_value"],
                    "has_read": True,
                    "has_write": False
                }
            
            # Process timeseries (holding registers and input registers)
            for ts in slave.get("timeseries", []):
                address = ts.get("address", 0)
                point_type = self._get_point_type_from_function_code(ts.get("functionCode"))
                key = (point_type, address, unit_id)
                data_type = self.TB_TYPE_TO_DATA_TYPE.get(ts.get("type", "uint16"), ModbusDataType.UINT16)
                
                if key in points_map:
                    points_map[key]["has_read"] = True
                    if not points_map[key]["name"].startswith("set_"):
                        points_map[key]["name"] = ts.get("tag", points_map[key]["name"])
                else:
                    points_map[key] = {
                        "name": ts.get("tag", "Imported Point"),
                        "description": self.default_values["description"],
                        "type": point_type,
                        "data_type": data_type,
                        "address": address,
                        "len": ts.get("objectsCount", self.default_values["len"]),
                        "unit_id": unit_id,
                        "formula": self.default_values["formula"],
                        "unit": self.default_values["unit"],
                        "min_value": self.default_values["min_value"],
                        "max_value": self.default_values["max_value"],
                        "has_read": True,
                        "has_write": False
                    }
            
            # Process RPC (writable points)
            for rpc in slave.get("rpc", []):
                address = rpc.get("address", 0)
                point_type = self._get_point_type_from_function_code(rpc.get("functionCode"))
                key = (point_type, address, unit_id)
                data_type = self.TB_TYPE_TO_DATA_TYPE.get(rpc.get("type", "uint16"), ModbusDataType.UINT16)
                
                if key in points_map:
                    points_map[key]["has_write"] = True
                    rpc_name = rpc.get("tag", "")
                    if rpc_name.startswith("set_"):
                        points_map[key]["name"] = rpc_name[4:]
                else:
                    rpc_name = rpc.get("tag", "Imported Point")
                    if rpc_name.startswith("set_"):
                        rpc_name = rpc_name[4:]
                    
                    points_map[key] = {
                        "name": rpc_name,
                        "description": self.default_values["description"],
                        "type": point_type,
                        "data_type": data_type,
                        "address": address,
                        "len": rpc.get("objectsCount", self.default_values["len"]),
                        "unit_id": unit_id,
                        "formula": self.default_values["formula"],
                        "unit": self.default_values["unit"],
                        "min_value": self.default_values["min_value"],
                        "max_value": self.default_values["max_value"],
                        "has_read": False,
                        "has_write": True
                    }
            
            for point_data in points_map.values():
                point_type = point_data["type"]
                can_write = point_type in [ModbusPointType.COIL, ModbusPointType.HOLDING_REGISTER]
                
                if not can_write and point_data["has_write"]:
                    logger.warning(f"Point {point_data['name']} (type: {point_type}) cannot be written, ignoring write capability")
                    point_data["has_write"] = False
                
                point = ModbusPoint(
                    controller_id=controller.id,
                    name=point_data["name"],
                    description=point_data["description"],
                    type=point_data["type"],
                    data_type=point_data["data_type"],
                    address=point_data["address"],
                    len=point_data["len"],
                    unit_id=point_data["unit_id"],
                    formula=point_data["formula"],
                    unit=point_data["unit"],
                    min_value=point_data["min_value"],
                    max_value=point_data["max_value"],
                )
                db.add(point)
            
            controllers.append(controller)
        
        await db.commit()
        return controllers
    
    def _validate_config(self, config: Dict[str, Any], format: ConfigFormat) -> ModbusConfigValidationResult:
        """Validate configuration format and content"""
        errors = []
        warnings = []
        
        if format == ConfigFormat.NATIVE:
            if "master" in config and "slaves" in config.get("master", {}):
                raise ModbusConfigFormatMismatchException(
                    f"Configuration appears to be in ThingsBoard format, but native format was expected. "
                    f"Please select 'thingsboard' format for this file."
                )
            
            # Check for both single and multi-controller formats
            has_single = "controller" in config and "points" in config
            has_multi = "controllers" in config
            
            if not has_single and not has_multi:
                errors.append("Missing 'controller' and 'points' sections or 'controllers' section in native format")
            
            if has_single:
                controller = config["controller"]
                required_fields = ["name", "host", "port"]
                for field in required_fields:
                    if field not in controller:
                        errors.append(f"Missing required field '{field}' in controller")
                
                for i, point in enumerate(config["points"]):
                    required_fields = ["name", "type", "data_type", "address"]
                    for field in required_fields:
                        if field not in point:
                            errors.append(f"Point {i}: Missing required field '{field}'")
                    
                    if "type" in point and point["type"] not in [t.value for t in ModbusPointType]:
                        errors.append(f"Point {i}: Invalid type '{point['type']}'")
            
            if has_multi:
                for i, controller_data in enumerate(config["controllers"]):
                    required_fields = ["name", "host", "port"]
                    for field in required_fields:
                        if field not in controller_data:
                            errors.append(f"Controller {i}: Missing required field '{field}'")
                    
                    points_data = controller_data.get("points", [])
                    for j, point in enumerate(points_data):
                        required_fields = ["name", "type", "data_type", "address"]
                        for field in required_fields:
                            if field not in point:
                                errors.append(f"Controller {i} Point {j}: Missing required field '{field}'")
                        
                        if "type" in point and point["type"] not in [t.value for t in ModbusPointType]:
                            errors.append(f"Controller {i} Point {j}: Invalid type '{point['type']}'")
        
        elif format == ConfigFormat.THINGSBOARD:
            if ("controller" in config and "points" in config) or "controllers" in config:
                raise ModbusConfigFormatMismatchException(
                    f"Configuration appears to be in native format, but ThingsBoard format was expected. "
                    f"Please select 'native' format for this file."
                )
            
            if "master" not in config:
                errors.append("Missing 'master' section in ThingsBoard format")
            
            if "master" in config:
                master = config["master"]
                if "slaves" not in master:
                    errors.append("Missing 'slaves' section in master")
                
                if "slaves" in master:
                    for i, slave in enumerate(master["slaves"]):
                        required_fields = ["host", "port", "deviceName"]
                        for field in required_fields:
                            if field not in slave:
                                errors.append(f"Slave {i}: Missing required field '{field}'")
                        
                        # Validate attributes, timeseries, and rpc
                        for section in ["attributes", "timeseries", "rpc"]:
                            if section in slave:
                                for j, item in enumerate(slave[section]):
                                    if "tag" not in item:
                                        errors.append(f"Slave {i} {section} {j}: Missing 'tag' field")
                                    if "functionCode" not in item:
                                        errors.append(f"Slave {i} {section} {j}: Missing 'functionCode' field")
                                    if "address" not in item:
                                        errors.append(f"Slave {i} {section} {j}: Missing 'address' field")
        
        return ModbusConfigValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _get_point_type_from_function_code(self, function_code: int) -> str:
        """Get point type from function code"""
        return self.FUNCTION_CODE_TO_TYPE.get(function_code, ModbusPointType.HOLDING_REGISTER)
    
    async def _get_controller(self, controller_id: str, db: AsyncSession) -> ModbusController:
        """Get controller by ID"""
        result = await db.execute(
            select(ModbusController).where(ModbusController.id == controller_id)
        )
        controller = result.scalar_one_or_none()
        if not controller:
            raise ModbusConfigException(f"Controller {controller_id} not found")
        return controller
    
    async def _get_controller_points(self, controller_id: str, db: AsyncSession) -> List[ModbusPoint]:
        """Get all points for a controller"""
        result = await db.execute(
            select(ModbusPoint).where(ModbusPoint.controller_id == controller_id)
        )
        return result.scalars().all()
    
    async def _get_point_by_name_and_controller(self, name: str, controller_id: str, db: AsyncSession) -> Optional[ModbusPoint]:
        """Get point by name and controller ID"""
        result = await db.execute(
            select(ModbusPoint).where(
                ModbusPoint.name == name,
                ModbusPoint.controller_id == controller_id
            )
        )
        return result.scalar_one_or_none()

async def export_modbus_config(
    controller_id: str, 
    db: AsyncSession, 
    format: str = "native"
) -> Dict[str, Any]:
    """Export Modbus configuration"""
    manager = ModbusConfigManager()
    return await manager.export_config(controller_id, db, ConfigFormat(format))

async def import_modbus_config(
    config: Dict[str, Any], 
    db: AsyncSession, 
    format: str = "native",
    overwrite: bool = False
) -> List[ModbusController]:
    """Import Modbus configuration"""
    manager = ModbusConfigManager()
    return await manager.import_config(config, db, ConfigFormat(format), overwrite)

def validate_modbus_config(config: Dict[str, Any], format: str = "native") -> ModbusConfigValidationResult:
    """Validate Modbus configuration"""
    manager = ModbusConfigManager()
    return manager.validate_config(config, ConfigFormat(format)) 