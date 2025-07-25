import logging
from enum import Enum
from datetime import datetime
from dataclasses import dataclass
from models.modbus_point import ModbusPoint
from typing import Dict, List, Any, Optional
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from models.modbus_controller import ModbusController
from utils.custom_exception import ModbusConfigException, ModbusControllerDuplicateException, ModbusConfigFormatException, ServerException

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

class ImportMode(str, Enum):
    """Import mode for handling duplicate controllers and points"""
    SKIP_CONTROLLER = "skip_controller"
    OVERWRITE_CONTROLLER = "overwrite_controller"
    SKIP_DUPLICATES_POINT = "skip_duplicates_point"
    OVERWRITE_DUPLICATES_POINT = "overwrite_duplicates_point"

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
        controller_id: str, 
        db: AsyncSession = None, 
        format: ConfigFormat = ConfigFormat.NATIVE
    ) -> Dict[str, Any]:
        """
        Export Modbus configuration for a single controller
        
        Args:
            controller_id: Controller ID to export
            db: Database session
            format: Export format (native or thingsboard)
            
        Returns:
            Configuration dictionary in the specified format
        """
        try:
            if db is None:
                raise ModbusConfigException("Database session (db) is required for export.")

            if not controller_id:
                raise ModbusConfigException("Controller ID is required for export.")

            # Get the specified controller
            controller = await self._get_controller(controller_id, db)
            
            # Get points for this controller
            points_result = await db.execute(
                select(ModbusPoint).where(ModbusPoint.controller_id == controller.id)
            )
            points = points_result.scalars().all()
            
            if format == ConfigFormat.NATIVE:
                return self._export_native_format(controller, points)
            elif format == ConfigFormat.THINGSBOARD:
                return self._export_thingsboard_format(controller, points)
            else:
                raise ModbusConfigFormatException(f"Unsupported format: {format}")
                
        except (ModbusConfigException, ModbusConfigFormatException):
            raise
        except Exception as e:
            raise ServerException(f"Export failed: {str(e)}")
    
    async def import_config(
        self, 
        config: Dict[str, Any], 
        db: AsyncSession, 
        format: ConfigFormat = ConfigFormat.NATIVE,
        import_mode: ImportMode = ImportMode.SKIP_CONTROLLER
    ) -> Dict[str, Any]:
        """
        Import Modbus configuration from the specified format (single controller only)
        
        Args:
            config: Configuration dictionary
            db: Database session
            format: Import format (native or thingsboard)
            import_mode: Import mode for handling duplicates
            
        Returns:
            Import result with detailed information
        """
        try:
            # Validate configuration format - will raise ModbusConfigFormatException for format errors
            self._validate_config(config, format)
            
            if format == ConfigFormat.NATIVE:
                return await self._import_native_format(config, db, import_mode)
            elif format == ConfigFormat.THINGSBOARD:
                return await self._import_thingsboard_format(config, db, import_mode)
            else:
                raise ModbusConfigFormatException(f"Unsupported format: {format}")
                
        except (ModbusControllerDuplicateException, ModbusConfigException, ModbusConfigFormatException):
            raise
        except Exception as e:
            raise ServerException(f"Import failed: {str(e)}")
    
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
    
    async def _import_native_format(self, config: Dict[str, Any], db: AsyncSession, import_mode: ImportMode) -> Dict[str, Any]:
        """Import from native format with specified import mode (single controller only)"""
        try:
            # Configuration format is already validated in _validate_config
            controller_data = config.get("controller", {})
            points_data = config.get("points", [])
            
            result = await self._process_controller_import(
                controller_data, points_data, db, import_mode
            )
            
            return {
                "controller_result": result,
                "total_points": len(points_data)
            }
        except (ModbusConfigException, ModbusConfigFormatException):
            raise
        except Exception as e:
            raise ServerException(f"Import failed: {str(e)}")
    
    async def _process_controller_import(
        self, 
        controller_data: Dict[str, Any], 
        points_data: List[Dict[str, Any]], 
        db: AsyncSession, 
        import_mode: ImportMode
    ) -> Dict[str, Any]:
        """Process controller import based on import mode"""
        try:
            # Check for existing controller
            existing_controller = await db.execute(
                select(ModbusController).where(
                    ModbusController.host == controller_data.get("host"),
                    ModbusController.port == controller_data.get("port")
                )
            )
            existing_controller = existing_controller.scalar_one_or_none()
            
            if existing_controller:
                # Controller exists, handle based on import mode
                if import_mode == ImportMode.SKIP_CONTROLLER:
                    return self._create_controller_result(
                        None,
                        controller_data.get("name"),
                        "skipped",
                        "Controller already exists",
                        []
                    )
                
                elif import_mode == ImportMode.OVERWRITE_CONTROLLER:
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
                    
                    # Create all new points
                    point_results = []
                    for point_data in points_data:
                        point = ModbusPoint(
                            controller_id=existing_controller.id,
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
                        await db.flush()
                        
                        point_results.append({
                            "point_id": str(point.id),
                            "point_name": point.name,
                            "status": "success",
                            "message": "Created successfully"
                        })
                    
                    await db.commit()
                    
                    return self._create_controller_result(
                        str(existing_controller.id),
                        existing_controller.name,
                        "success",
                        "Controller and points overwritten successfully",
                        point_results
                    )
                
                elif import_mode in [ImportMode.SKIP_DUPLICATES_POINT, ImportMode.OVERWRITE_DUPLICATES_POINT]:
                    point_results = []
                    
                    for point_data in points_data:
                        try:
                            result = await self._process_single_point(point_data, existing_controller, point_data.get("unit_id", 1), db, import_mode)
                            point_results.append(result)
                        except ModbusConfigException as e:
                            point_results.append({
                                "point_id": None,
                                "point_name": point_data.get("name", "unknown"),
                                "status": "error",
                                "message": f"Configuration error: {str(e)}"
                            })
                        except Exception as e:
                            logger.error(f"Error processing point {point_data.get('name', 'unknown')}: {str(e)}")
                            point_results.append({
                                "point_id": None,
                                "point_name": point_data.get("name", "unknown"),
                                "status": "error",
                                "message": f"Point error: {str(e)}"
                            })
                    
                    await db.commit()
                    
                    return self._determine_controller_result_status(
                        point_results,
                        str(existing_controller.id),
                        existing_controller.name,
                        "Controller updated with point changes",
                        "All points failed or skipped"
                    )
            
            else:
                # Controller doesn't exist, create new one
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
                
                # Create all points
                point_results = []
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
                    await db.flush()
                    
                    point_results.append({
                        "point_id": str(point.id),
                        "point_name": point.name,
                        "status": "success",
                        "message": "Created successfully"
                    })
                
                await db.commit()
                
                return self._create_controller_result(
                    str(controller.id),
                    controller.name,
                    "success",
                    "Controller and points created successfully",
                    point_results
                )
        except (ModbusConfigException, ModbusConfigFormatException):
            raise
        except Exception as e:
            raise ServerException(f"Controller import failed: {str(e)}")
    
    async def _import_thingsboard_format(self, config: Dict[str, Any], db: AsyncSession, import_mode: ImportMode) -> Dict[str, Any]:
        """Import from ThingsBoard format with specified import mode (single controller only)"""
        try:
            # Configuration format is already validated in _validate_config
            master = config.get("master", {})
            slaves = master.get("slaves", [])
            
            slave = slaves[0]
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
                if import_mode == ImportMode.SKIP_CONTROLLER:
                    result = self._create_controller_result(
                        None,
                        existing_controller.name,
                        "skipped",
                        "Controller already exists",
                        []
                    )
                elif import_mode == ImportMode.OVERWRITE_CONTROLLER:
                    await db.execute(
                        delete(ModbusPoint).where(ModbusPoint.controller_id == existing_controller.id)
                    )
                    await db.execute(
                        delete(ModbusController).where(ModbusController.id == existing_controller.id)
                    )
                    await db.flush()
                    
                    controller = ModbusController(
                        name=slave.get("deviceName", "Imported Controller"),
                        host=host,
                        port=port,
                        timeout=slave.get("timeout", self.default_values["timeout"]),
                        status=False
                    )
                    
                    db.add(controller)
                    await db.flush()
                    
                    result = await self._process_points_with_error_handling(slave, controller, db, import_mode, "Controller overwritten successfully")
                elif import_mode in [ImportMode.SKIP_DUPLICATES_POINT, ImportMode.OVERWRITE_DUPLICATES_POINT]:
                    result = await self._process_points_with_error_handling(slave, existing_controller, db, import_mode, "Controller updated with point changes")
            else:
                # Create new controller
                controller = ModbusController(
                    name=slave.get("deviceName", "Imported Controller"),
                    host=host,
                    port=port,
                    timeout=slave.get("timeout", self.default_values["timeout"]),
                    status=False
                )
                
                db.add(controller)
                await db.flush()
                
                result = await self._process_points_with_error_handling(slave, controller, db, import_mode, "Controller and points created successfully")
            
            all_point_tags = set()
            for attr in slave.get("attributes", []):
                all_point_tags.add(attr.get("tag"))
            for ts in slave.get("timeseries", []):
                all_point_tags.add(ts.get("tag"))
            for rpc in slave.get("rpc", []):
                all_point_tags.add(rpc.get("tag"))
            total_points = len(all_point_tags)
            
            return {
                "controller_result": result,
                "total_points": total_points
            }
        except (ModbusConfigException, ModbusConfigFormatException):
            raise
        except Exception as e:
            raise ServerException(f"Import failed: {str(e)}")
    
    async def _process_points_with_error_handling(self, slave: Dict[str, Any], controller: ModbusController, db: AsyncSession, import_mode: ImportMode, success_message: str) -> Dict[str, Any]:
        """Process points with error handling and return controller result"""
        try:
            point_results = await self._process_thingsboard_points(slave, controller, db, import_mode)
            await db.commit()
            return self._determine_controller_result_status(
                point_results, 
                str(controller.id), 
                controller.name, 
                success_message,
                "All points failed to import"
            )
        except ModbusConfigException as e:
            raise
        except Exception as e:
            raise ServerException(f"Failed to process points: {str(e)}")

    async def _process_thingsboard_points(self, slave: Dict[str, Any], controller: ModbusController, db: AsyncSession, import_mode: ImportMode) -> List[Dict[str, Any]]:
        """Process ThingsBoard points for a controller"""
        point_results = []
        unit_id = slave.get("unitId", self.default_values["unit_id"])
        
        # Collect all points from different sections and deduplicate by tag name
        all_points = {}
        
        # Process attributes (coils and discrete inputs)
        for attr in slave.get("attributes", []):
            tag = attr.get("tag")
            if tag not in all_points:
                all_points[tag] = {
                    "data": attr,
                    "sections": ["attribute"]
                }
            else:
                # If tag already exists, merge sections
                all_points[tag]["sections"].append("attribute")
        
        # Process timeseries (holding registers and input registers)
        for ts in slave.get("timeseries", []):
            tag = ts.get("tag")
            if tag not in all_points:
                all_points[tag] = {
                    "data": ts,
                    "sections": ["timeseries"]
                }
            else:
                # If tag already exists, merge sections
                all_points[tag]["sections"].append("timeseries")
        
        # Process RPC (writable points)
        for rpc in slave.get("rpc", []):
            tag = rpc.get("tag")
            if tag not in all_points:
                all_points[tag] = {
                    "data": rpc,
                    "sections": ["rpc"]
                }
            else:
                # If tag already exists, merge sections
                all_points[tag]["sections"].append("rpc")
        
        # Process each unique point
        for tag, point_info in all_points.items():
            try:
                result = await self._process_thingsboard_point(point_info["data"], controller, unit_id, db, import_mode, "+".join(point_info["sections"]))
                point_results.append(result)
            except ModbusConfigException as e:
                point_results.append({
                    "point_id": None,
                    "point_name": tag,
                    "status": "error",
                    "message": f"Configuration error: {str(e)}"
                })
            except Exception as e:
                logger.error(f"Error processing point {tag}: {str(e)}")
                point_results.append({
                    "point_id": None,
                    "point_name": tag,
                    "status": "error",
                    "message": f"Point error: {str(e)}"
                })
        
        return point_results
    
    async def _process_single_point(self, point_data: Dict[str, Any], controller: ModbusController, unit_id: int, db: AsyncSession, import_mode: ImportMode) -> Dict[str, Any]:
        """Process a single native format point"""
        try:
            # Check for existing point
            existing_point = await db.execute(
                select(ModbusPoint).where(
                    ModbusPoint.controller_id == controller.id,
                    ModbusPoint.unit_id == unit_id,
                    ModbusPoint.address == point_data.get("address"),
                    ModbusPoint.type == point_data.get("type")
                )
            )
            existing_point = existing_point.scalar_one_or_none()

            if existing_point:
                if import_mode == ImportMode.SKIP_DUPLICATES_POINT:
                    return {
                        "point_id": None,
                        "point_name": point_data.get("name", "Imported Point"),
                        "status": "skipped",
                        "message": "Point already exists"
                    }
                else:  # OVERWRITE_DUPLICATES_POINT
                    await db.execute(
                        update(ModbusPoint)
                        .where(ModbusPoint.id == existing_point.id)
                        .values(
                            name=point_data.get("name", "Imported Point"),
                            description=point_data.get("description"),
                            data_type=point_data.get("data_type"),
                            len=point_data.get("len", self.default_values["len"]),
                            formula=point_data.get("formula"),
                            unit=point_data.get("unit"),
                            min_value=point_data.get("min_value"),
                            max_value=point_data.get("max_value"),
                            updated_at=datetime.now()
                        )
                    )

                    return {
                        "point_id": str(existing_point.id),
                        "point_name": point_data.get("name", "Imported Point"),
                        "status": "success",
                        "message": "Point updated successfully"
                    }
            else:
                # Create new point
                point = ModbusPoint(
                    controller_id=controller.id,
                    name=point_data.get("name", "Imported Point"),
                    description=point_data.get("description"),
                    type=point_data.get("type"),
                    data_type=point_data.get("data_type"),
                    address=point_data.get("address"),
                    len=point_data.get("len", self.default_values["len"]),
                    unit_id=unit_id,
                    formula=point_data.get("formula"),
                    unit=point_data.get("unit"),
                    min_value=point_data.get("min_value"),
                    max_value=point_data.get("max_value")
                )
                db.add(point)
                await db.flush()

                return {
                    "point_id": str(point.id),
                    "point_name": point.name,
                    "status": "success",
                    "message": "Point created successfully"
                }
        except ModbusConfigException as e:
            raise
        except Exception as e:
            raise ModbusConfigException(f"Point processing error: {str(e)}")
    
    async def _process_thingsboard_point(self, point_data: Dict[str, Any], controller: ModbusController, unit_id: int, db: AsyncSession, import_mode: ImportMode, point_type: str) -> Dict[str, Any]:
        """Process a single ThingsBoard point"""
        try:
            address = point_data.get("address", 0)
            function_code = point_data.get("functionCode")

            point_type_enum = self._get_point_type_from_function_code(function_code)
            if point_type_enum is None:
                raise ModbusConfigException(f"Unsupported function code {function_code} for point {point_data.get('tag', 'unknown')}")

            data_type = self.TB_TYPE_TO_DATA_TYPE.get(point_data.get("type", "uint16"), ModbusDataType.UINT16)

            # Check for existing point
            existing_point = await db.execute(
                select(ModbusPoint).where(
                    ModbusPoint.controller_id == controller.id,
                    ModbusPoint.unit_id == unit_id,
                    ModbusPoint.address == address,
                    ModbusPoint.type == point_type_enum
                )
            )
            existing_point = existing_point.scalar_one_or_none()

            if existing_point:
                if import_mode == ImportMode.SKIP_DUPLICATES_POINT:
                    return {
                        "point_id": None,
                        "point_name": point_data.get("tag", "Imported Point"),
                        "status": "skipped",
                        "message": "Point already exists"
                    }
                else:  # OVERWRITE_DUPLICATES_POINT
                    await db.execute(
                        update(ModbusPoint)
                        .where(ModbusPoint.id == existing_point.id)
                        .values(
                            name=point_data.get("tag", "Imported Point"),
                            description=self.default_values["description"],
                            data_type=data_type,
                            len=point_data.get("objectsCount", self.default_values["len"]),
                            formula=self.default_values["formula"],
                            unit=self.default_values["unit"],
                            min_value=self.default_values["min_value"],
                            max_value=self.default_values["max_value"],
                            updated_at=datetime.now()
                        )
                    )

                    return {
                        "point_id": str(existing_point.id),
                        "point_name": point_data.get("tag", "Imported Point"),
                        "status": "success",
                        "message": "Point updated successfully"
                    }
            else:
                # Create new point
                point = ModbusPoint(
                    controller_id=controller.id,
                    name=point_data.get("tag", "Imported Point"),
                    description=self.default_values["description"],
                    type=point_type_enum,
                    data_type=data_type,
                    address=address,
                    len=point_data.get("objectsCount", self.default_values["len"]),
                    unit_id=unit_id,
                    formula=self.default_values["formula"],
                    unit=self.default_values["unit"],
                    min_value=self.default_values["min_value"],
                    max_value=self.default_values["max_value"]
                )
                db.add(point)
                await db.flush()

                return {
                    "point_id": str(point.id),
                    "point_name": point.name,
                    "status": "success",
                    "message": "Point created successfully"
                }
        except ModbusConfigException as e:
            raise
        except Exception as e:
            raise ModbusConfigException(f"Point processing error: {str(e)}")
    
    def _validate_config(self, config: Dict[str, Any], format: ConfigFormat) -> ModbusConfigValidationResult:
        """Validate configuration format and content"""
        errors = []
        warnings = []
        
        if format == ConfigFormat.NATIVE:
            if "master" in config and "slaves" in config.get("master", {}):
                raise ModbusConfigFormatException(
                    f"Configuration appears to be in ThingsBoard format, but native format was expected. "
                    f"Please select 'thingsboard' format for this file."
                )
            
            # Check for single controller format only
            if "controller" not in config or "points" not in config:
                raise ModbusConfigFormatException("Missing 'controller' and 'points' sections in native format")
            
            if "controller" in config:
                controller = config["controller"]
                required_fields = ["name", "host", "port"]
                for field in required_fields:
                    if field not in controller:
                        raise ModbusConfigFormatException(f"Missing required field '{field}' in controller")
                
                for i, point in enumerate(config["points"]):
                    required_fields = ["name", "type", "data_type", "address"]
                    for field in required_fields:
                        if field not in point:
                            raise ModbusConfigFormatException(f"Point {i}: Missing required field '{field}'")
                    
                    if "type" in point and point["type"] not in [t.value for t in ModbusPointType]:
                        raise ModbusConfigFormatException(f"Point {i}: Invalid type '{point['type']}'")
        
        elif format == ConfigFormat.THINGSBOARD:
            if "controller" in config and "points" in config:
                raise ModbusConfigFormatException(
                    f"Configuration appears to be in native format, but ThingsBoard format was expected. "
                    f"Please select 'native' format for this file."
                )
            
            if "master" not in config:
                raise ModbusConfigFormatException("Missing 'master' section in ThingsBoard format")
            
            if "master" in config:
                master = config["master"]
                if "slaves" not in master:
                    raise ModbusConfigFormatException("Missing 'slaves' section in master")
                
                if "slaves" in master:
                    slaves = master["slaves"]
                    if len(slaves) == 0:
                        raise ModbusConfigFormatException("No slaves found in ThingsBoard configuration")
                    elif len(slaves) > 1:
                        raise ModbusConfigFormatException("Only single controller import is supported. Multiple slaves found.")
                    
                    for i, slave in enumerate(slaves):
                        required_fields = ["host", "port", "deviceName"]
                        for field in required_fields:
                            if field not in slave:
                                raise ModbusConfigFormatException(f"Slave {i}: Missing required field '{field}'")
                        
                        # Validate attributes, timeseries, and rpc
                        for section in ["attributes", "timeseries", "rpc"]:
                            if section in slave:
                                for j, item in enumerate(slave[section]):
                                    if "tag" not in item:
                                        raise ModbusConfigFormatException(f"Slave {i} {section} {j}: Missing 'tag' field")
                                    if "functionCode" not in item:
                                        raise ModbusConfigFormatException(f"Slave {i} {section} {j}: Missing 'functionCode' field")
                                    if "address" not in item:
                                        raise ModbusConfigFormatException(f"Slave {i} {section} {j}: Missing 'address' field")
        
        return ModbusConfigValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _get_point_type_from_function_code(self, function_code: int) -> Optional[str]:
        """Get point type from function code"""
        return self.FUNCTION_CODE_TO_TYPE.get(function_code, None)
    
    async def _get_controller(self, controller_id: str, db: AsyncSession) -> ModbusController:
        """Get controller by ID"""
        result = await db.execute(
            select(ModbusController).where(ModbusController.id == controller_id)
        )
        controller = result.scalar_one_or_none()
        if not controller:
            raise ServerException(f"Controller {controller_id} not found")
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

    def _determine_controller_result_status(self, point_results: List[Dict[str, Any]], controller_id: str, controller_name: str, success_message: str, failed_message: str) -> Dict[str, Any]:
        """Determine controller result status based on point results"""
        success_points = [p for p in point_results if p["status"] == "success"]
        error_points = [p for p in point_results if p["status"] == "error"]
        skipped_points = [p for p in point_results if p["status"] == "skipped"]
        
        if len(success_points) > 0:
            return self._create_controller_result(
                controller_id,
                controller_name,
                "success",
                success_message,
                point_results
            )
        elif len(error_points) > 0 and len(success_points) == 0 and len(skipped_points) == 0:
            return self._create_controller_result(
                controller_id,
                controller_name,
                "failed",
                "All points failed to import",
                point_results
            )
        elif len(skipped_points) > 0 and len(success_points) == 0 and len(error_points) == 0:
            return self._create_controller_result(
                controller_id,
                controller_name,
                "failed",
                "All points already exist",
                point_results
            )
        else:
            return self._create_controller_result(
                controller_id,
                controller_name,
                "success",
                success_message,
                point_results
            )

    def _create_controller_result(self, controller_id: str, controller_name: str, status: str, message: str, points: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a standardized controller result"""
        if points is None:
            points = []
        
        return {
            "controller_id": controller_id,
            "controller_name": controller_name,
            "status": status,
            "message": message,
            "points": points
        }

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
    return await manager.import_config(config, db, ConfigFormat(format), ImportMode(overwrite))