import logging
from enum import Enum
from datetime import datetime
from models.modbus_point import ModbusPoint
from typing import Dict, List, Any, Optional
from .validator import ModbusConfigValidator
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from .data_converter import ModbusDataConverter
from models.modbus_controller import ModbusController
from utils.custom_exception import (
    ModbusConfigException, 
    ModbusControllerDuplicateException, 
    ModbusConfigFormatException, 
    ServerException
)

logger = logging.getLogger(__name__)

class ConfigFormat(str, Enum):
    """Supported configuration formats"""
    NATIVE = "native"
    THINGSBOARD = "thingsboard"

class ImportMode(str, Enum):
    """Import mode for handling duplicate controllers and points"""
    SKIP_CONTROLLER = "skip_controller"
    OVERWRITE_CONTROLLER = "overwrite_controller"
    SKIP_DUPLICATES_POINT = "skip_duplicates_point"
    OVERWRITE_DUPLICATES_POINT = "overwrite_duplicates_point"

class ModbusConfigManager:
    """Centralized Modbus configuration management"""
    
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
        db: AsyncSession, 
        format: ConfigFormat = ConfigFormat.NATIVE
    ) -> Dict[str, Any]:
        """Export Modbus configuration"""
        try:
            if not controller_id:
                raise ModbusConfigException("Controller ID is required for export.")

            controller = await self._get_controller(controller_id, db)
            points = await self._get_controller_points(controller_id, db)
            
            if format == ConfigFormat.NATIVE:
                return self._export_native_format(controller, points)
            elif format == ConfigFormat.THINGSBOARD:
                return ModbusDataConverter.convert_points_to_thingsboard_format(controller, points)
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
        """Import Modbus configuration"""
        try:
            # Validate configuration
            ModbusConfigValidator.validate_config(config, format.value)
            
            if format == ConfigFormat.NATIVE:
                return await self._process_native_import(config, db, import_mode)
            elif format == ConfigFormat.THINGSBOARD:
                return await self._process_thingsboard_import(config, db, import_mode)
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
    
    async def _process_native_import(self, config: Dict[str, Any], db: AsyncSession, import_mode: ImportMode) -> Dict[str, Any]:
        """Process native format import"""
        controller_data = config.get("controller", {})
        points_data = config.get("points", [])
        
        result = await self._process_import(controller_data, points_data, db, import_mode)
        
        return {
            "controller_result": result,
            "total_points": len(points_data)
        }
    
    async def _process_thingsboard_import(self, config: Dict[str, Any], db: AsyncSession, import_mode: ImportMode) -> Dict[str, Any]:
        """Process ThingsBoard format import"""
        slave = config.get("master", {}).get("slaves", [])[0]
        
        # Convert to unified format
        controller_data = {
            "name": slave.get("deviceName", "Imported Controller"),
            "host": slave.get("host", "localhost"),
            "port": slave.get("port", 502),
            "timeout": slave.get("timeout", self.default_values["timeout"])
        }
        
        points_data = ModbusDataConverter.convert_thingsboard_to_unified_format(slave)
        
        result = await self._process_import(controller_data, points_data, db, import_mode)
        
        return {
            "controller_result": result,
            "total_points": len(points_data)
        }
    
    async def _process_import(
        self, 
        controller_data: Dict[str, Any], 
        points_data: List[Dict[str, Any]], 
        db: AsyncSession, 
        import_mode: ImportMode
    ) -> Dict[str, Any]:
        """Unified import processing logic"""
        try:
            # Check for existing controller
            existing_controller = await self._find_existing_controller(controller_data, db)
            
            if existing_controller:
                return await self._handle_existing_controller(
                    existing_controller, controller_data, points_data, db, import_mode
                )
            else:
                return await self._create_new_controller_with_points(
                    controller_data, points_data, db
                )
                
        except Exception as e:
            raise ServerException(f"Import processing failed: {str(e)}")
    
    async def _handle_existing_controller(
        self, 
        existing_controller: ModbusController,
        controller_data: Dict[str, Any],
        points_data: List[Dict[str, Any]],
        db: AsyncSession,
        import_mode: ImportMode
    ) -> Dict[str, Any]:
        """Handle existing controller import"""
        if import_mode == ImportMode.SKIP_CONTROLLER:
            return self._create_controller_result(
                None, controller_data.get("name"), "skipped", "Controller already exists", []
            )
        
        elif import_mode == ImportMode.OVERWRITE_CONTROLLER:
            return await self._overwrite_controller_and_points(
                existing_controller, controller_data, points_data, db
            )
        
        elif import_mode in [ImportMode.SKIP_DUPLICATES_POINT, ImportMode.OVERWRITE_DUPLICATES_POINT]:
            return await self._update_controller_points(
                existing_controller, points_data, db, import_mode
            )
    
    async def _create_new_controller_with_points(
        self,
        controller_data: Dict[str, Any],
        points_data: List[Dict[str, Any]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Create new controller with points"""
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
        
        point_results = await self._create_all_points(controller, points_data, db)
        await db.commit()
        
        return self._create_controller_result(
            str(controller.id), controller.name, "success", 
            "Controller and points created successfully", point_results
        )
    
    async def _overwrite_controller_and_points(
        self,
        existing_controller: ModbusController,
        controller_data: Dict[str, Any],
        points_data: List[Dict[str, Any]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Overwrite controller and points"""
        # Update controller
        await db.execute(
            update(ModbusController)
            .where(ModbusController.id == existing_controller.id)
            .values(
                name=controller_data.get("name"),
                timeout=controller_data.get("timeout", 10)
            )
        )
        
        # Delete existing points
        await db.execute(
            delete(ModbusPoint).where(ModbusPoint.controller_id == existing_controller.id)
        )
        
        # Create new points
        point_results = await self._create_all_points(existing_controller, points_data, db)
        await db.commit()
        
        return self._create_controller_result(
            str(existing_controller.id), existing_controller.name, "success",
            "Controller and points overwritten successfully", point_results
        )
    
    async def _update_controller_points(
        self,
        existing_controller: ModbusController,
        points_data: List[Dict[str, Any]],
        db: AsyncSession,
        import_mode: ImportMode
    ) -> Dict[str, Any]:
        """Update controller points"""
        point_results = []
        
        for point_data in points_data:
            try:
                result = await self._process_single_point(
                    point_data, existing_controller, 
                    point_data.get("unit_id", 1), db, import_mode
                )
                point_results.append(result)
            except Exception as e:
                logger.error(f"Error processing point {point_data.get('name', 'unknown')}: {str(e)}")
                point_results.append({
                    "point_id": None,
                    "point_name": point_data.get("name", "unknown"),
                    "status": "error",
                    "message": "Point error"
                })
        
        await db.commit()
        
        return self._determine_controller_result_status(
            point_results, str(existing_controller.id), existing_controller.name,
            "Controller updated with point changes", "All points failed or skipped"
        )
    
    async def _create_all_points(
        self,
        controller: ModbusController,
        points_data: List[Dict[str, Any]],
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Create all points"""
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
        
        return point_results
    
    async def _process_single_point(
        self,
        point_data: Dict[str, Any],
        controller: ModbusController,
        unit_id: int,
        db: AsyncSession,
        import_mode: ImportMode
    ) -> Dict[str, Any]:
        """Process single point"""
        existing_point = await self._find_existing_point(controller, point_data, unit_id, db)
        
        if existing_point:
            if import_mode == ImportMode.SKIP_DUPLICATES_POINT:
                return {
                    "point_id": None,
                    "point_name": point_data.get("name", "Imported Point"),
                    "status": "skipped",
                    "message": "Point already exists"
                }
            else:  # OVERWRITE_DUPLICATES_POINT
                return await self._update_existing_point(existing_point, point_data, db)
        else:
            return await self._create_new_point(controller, point_data, unit_id, db)
    
    async def _find_existing_controller(self, controller_data: Dict[str, Any], db: AsyncSession) -> Optional[ModbusController]:
        """Find existing controller"""
        result = await db.execute(
            select(ModbusController).where(
                ModbusController.host == controller_data.get("host"),
                ModbusController.port == controller_data.get("port")
            )
        )
        return result.scalar_one_or_none()
    
    async def _find_existing_point(
        self,
        controller: ModbusController,
        point_data: Dict[str, Any],
        unit_id: int,
        db: AsyncSession
    ) -> Optional[ModbusPoint]:
        """Find existing point"""
        result = await db.execute(
            select(ModbusPoint).where(
                ModbusPoint.controller_id == controller.id,
                ModbusPoint.unit_id == unit_id,
                ModbusPoint.address == point_data.get("address"),
                ModbusPoint.type == point_data.get("type")
            )
        )
        return result.scalar_one_or_none()
    
    async def _update_existing_point(
        self,
        existing_point: ModbusPoint,
        point_data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Update existing point"""
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
                max_value=point_data.get("max_value")
            )
        )
        
        return {
            "point_id": str(existing_point.id),
            "point_name": point_data.get("name", "Imported Point"),
            "status": "success",
            "message": "Point updated successfully"
        }
    
    async def _create_new_point(
        self,
        controller: ModbusController,
        point_data: Dict[str, Any],
        unit_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Create new point"""
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
    
    def _determine_controller_result_status(
        self, 
        point_results: List[Dict[str, Any]], 
        controller_id: str, 
        controller_name: str, 
        success_message: str, 
        failed_message: str
    ) -> Dict[str, Any]:
        """Determine controller result status based on point results"""
        success_points = [p for p in point_results if p["status"] == "success"]
        error_points = [p for p in point_results if p["status"] == "error"]
        skipped_points = [p for p in point_results if p["status"] == "skipped"]
        
        if len(success_points) > 0:
            return self._create_controller_result(
                controller_id, controller_name, "success", success_message, point_results
            )
        elif len(error_points) > 0 and len(success_points) == 0 and len(skipped_points) == 0:
            return self._create_controller_result(
                controller_id, controller_name, "failed", "All points failed to import", point_results
            )
        elif len(skipped_points) > 0 and len(success_points) == 0 and len(error_points) == 0:
            return self._create_controller_result(
                controller_id, controller_name, "failed", "All points already exist", point_results
            )
        else:
            return self._create_controller_result(
                controller_id, controller_name, "success", success_message, point_results
            )
    
    def _create_controller_result(
        self, 
        controller_id: str, 
        controller_name: str, 
        status: str, 
        message: str, 
        points: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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

# Convenience functions for backward compatibility
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
    import_mode: str = "skip_controller"
) -> Dict[str, Any]:
    """Import Modbus configuration"""
    manager = ModbusConfigManager()
    return await manager.import_config(config, db, ConfigFormat(format), ImportMode(import_mode))