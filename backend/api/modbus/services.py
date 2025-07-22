import logging
import json
import tempfile
import os
from typing import Dict, Any, List
from datetime import datetime
from extensions.modbus import ModbusManager
from models.modbus_point import ModbusPoint
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models.modbus_controller import ModbusController
from .schema import (
    ModbusControllerCreateRequest, ModbusControllerUpdateRequest, ModbusControllerResponse,
    ModbusControllerListResponse, ModbusPointBatchCreateRequest, ModbusPointUpdateRequest,
    ModbusPointResponse, ModbusPointListResponse, ModbusPointBatchCreateResponse,
    ModbusPointDataResponse, ModbusPointValueResponse, ModbusControllerValuesResponse,
    ModbusPointWriteRequest, ModbusPointWriteResponse,
    ModbusConfigImportResponse, ModbusConfigValidationResponse,
    ConfigFormat
)
from utils.custom_exception import (
    ServerException, ModbusConnectionException, ModbusControllerNotFoundException,
    ModbusPointNotFoundException, ModbusReadException, ModbusValidationException, 
    ModbusWriteException, ModbusRangeValidationException, ModbusConfigException,
    ModbusConfigFormatMismatchException
)
from utils.modbus_config_manager import (
    ModbusConfigManager, ConfigFormat,
    export_modbus_config, import_modbus_config, validate_modbus_config
)

logger = logging.getLogger(__name__)

async def create_modbus_controller(request: ModbusControllerCreateRequest, db: AsyncSession, modbus: ModbusManager) -> ModbusControllerResponse:
    """Create Modbus controller (test connection first)"""
    try:
        test_client_id = modbus.create_tcp(
            host=request.host,
            port=request.port,
            timeout=request.timeout
        )
        
        success = await modbus.connect(test_client_id)
        
        modbus.disconnect(test_client_id)
        del modbus.clients[test_client_id]
        
        if not success:
            raise ModbusConnectionException(f"Unable to connect to {request.host}:{request.port}")
        
        controller = ModbusController(
            name=request.name,
            host=request.host,
            port=request.port,
            timeout=request.timeout,
            status=True
        )
        
        db.add(controller)
        await db.commit()
        await db.refresh(controller)
        
        return ModbusControllerResponse(
            id=controller.id,
            name=controller.name,
            host=controller.host,
            port=controller.port,
            timeout=controller.timeout,
            status=controller.status,
            created_at=controller.created_at.isoformat(),
            updated_at=controller.updated_at.isoformat()
        )
    except ModbusConnectionException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise ServerException(f"Failed to create controller: {str(e)}")

async def get_modbus_controllers(
    db: AsyncSession, 
    status: bool = None, 
    name: str = None
) -> ModbusControllerListResponse:
    """Get all Modbus controllers with filters"""
    try:
        query = select(ModbusController)
        
        if status is not None:
            query = query.where(ModbusController.status == status)
        
        if name:
            query = query.where(ModbusController.name.ilike(f"%{name}%"))
        
        query = query.order_by(ModbusController.created_at.desc())
        
        result = await db.execute(query)
        controllers = result.scalars().all()
        
        controller_list = [
            ModbusControllerResponse(
                id=ctrl.id,
                name=ctrl.name,
                host=ctrl.host,
                port=ctrl.port,
                timeout=ctrl.timeout,
                status=ctrl.status,
                created_at=ctrl.created_at.isoformat(),
                updated_at=ctrl.updated_at.isoformat()
            )
            for ctrl in controllers
        ]
        
        return ModbusControllerListResponse(
            total=len(controller_list),
            controllers=controller_list
        )
    except Exception as e:
        raise ServerException(f"Failed to get controller list: {str(e)}")

async def update_modbus_controller(controller_id: str, request: ModbusControllerUpdateRequest, db: AsyncSession, modbus: ModbusManager) -> ModbusControllerResponse:
    """Update Modbus controller (test connection first)"""
    try:
        result = await db.execute(
            select(ModbusController).where(ModbusController.id == controller_id)
        )
        controller = result.scalar_one_or_none()
        
        if not controller:
            raise ModbusControllerNotFoundException(f"Controller {controller_id} not found")
        
        new_host = request.host if request.host is not None else controller.host
        new_port = request.port if request.port is not None else controller.port
        new_timeout = request.timeout if request.timeout is not None else controller.timeout
        
        test_client_id = modbus.create_tcp(
            host=new_host,
            port=new_port,
            timeout=new_timeout
        )
        
        success = await modbus.connect(test_client_id)
        
        modbus.disconnect(test_client_id)
        del modbus.clients[test_client_id]
        
        if not success:
            raise ModbusConnectionException(f"Unable to connect to {new_host}:{new_port}")
        
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.host is not None:
            update_data["host"] = request.host
        if request.port is not None:
            update_data["port"] = request.port
        if request.timeout is not None:
            update_data["timeout"] = request.timeout
        
        update_data["status"] = True
        update_data["updated_at"] = datetime.now()
        
        await db.execute(
            update(ModbusController)
            .where(ModbusController.id == controller_id)
            .values(**update_data)
        )
        
        await db.commit()
        
        result = await db.execute(
            select(ModbusController).where(ModbusController.id == controller_id)
        )
        updated_controller = result.scalar_one()
        
        return ModbusControllerResponse(
            id=updated_controller.id,
            name=updated_controller.name,
            host=updated_controller.host,
            port=updated_controller.port,
            timeout=updated_controller.timeout,
            status=updated_controller.status,
            created_at=updated_controller.created_at.isoformat(),
            updated_at=updated_controller.updated_at.isoformat()
        )
        
    except (ModbusConnectionException, ModbusControllerNotFoundException):
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise ServerException(f"Failed to update controller: {str(e)}")

async def delete_modbus_controller(controller_id: str, db: AsyncSession) -> bool:
    """Delete Modbus controller (clear related points)"""
    try:
        await db.execute(
            delete(ModbusPoint).where(ModbusPoint.controller_id == controller_id)
        )
        
        result = await db.execute(
            delete(ModbusController).where(ModbusController.id == controller_id)
        )
        
        if result.rowcount == 0:
            raise ModbusControllerNotFoundException(f"Controller {controller_id} not found")
        
        await db.commit()
        return True
        
    except ModbusControllerNotFoundException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise ServerException(f"Failed to delete controller: {str(e)}")

async def test_modbus_controller(request: ModbusControllerCreateRequest, modbus: ModbusManager) -> Dict[str, Any]:
    """Test Modbus controller connection (do not save to database)"""
    try:
        test_client_id = modbus.create_tcp(
            host=request.host,
            port=request.port,
            timeout=request.timeout
        )
        
        start_time = datetime.now()
        success = await modbus.connect(test_client_id)
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds() * 1000  # milliseconds
        
        modbus.disconnect(test_client_id)
        del modbus.clients[test_client_id]
        
        if not success:
            raise ModbusConnectionException(f"Unable to connect to {request.host}:{request.port}")
        
        return {
            "host": request.host,
            "port": request.port,
            "timeout": request.timeout,
            "connected": True,
            "response_time_ms": round(response_time, 2),
            "test_time": start_time.isoformat()
        }
        
    except ModbusConnectionException:
        raise
    except Exception as e:
        try:
            if 'test_client_id' in locals() and test_client_id in modbus.clients:
                modbus.disconnect(test_client_id)
                del modbus.clients[test_client_id]
        except:
            pass
        
        raise ModbusConnectionException(f"Connection test failed: {str(e)}")

async def create_modbus_points_batch(request: ModbusPointBatchCreateRequest, db: AsyncSession) -> ModbusPointBatchCreateResponse:
    """Create multiple Modbus points for a controller"""
    try:
        controller_result = await db.execute(
            select(ModbusController).where(ModbusController.id == request.controller_id)
        )
        if not controller_result.scalar_one_or_none():
            raise ModbusControllerNotFoundException(f"Controller {request.controller_id} not found")
        
        created_points = []
        
        for point_request in request.points:
            point = ModbusPoint(
                controller_id=request.controller_id,
                name=point_request.name,
                description=point_request.description,
                type=point_request.type,
                data_type=point_request.data_type,
                address=point_request.address,
                len=point_request.len,
                unit_id=point_request.unit_id,
                formula=point_request.formula,
                unit=point_request.unit,
                min_value=point_request.min_value,
                max_value=point_request.max_value
            )
            
            db.add(point)
            created_points.append(point)
        
        await db.commit()
        
        for point in created_points:
            await db.refresh(point)
        
        point_responses = [
            ModbusPointResponse(
                id=point.id,
                controller_id=point.controller_id,
                name=point.name,
                description=point.description,
                type=point.type,
                data_type=point.data_type,
                address=point.address,
                len=point.len,
                unit_id=point.unit_id,
                formula=point.formula,
                unit=point.unit,
                min_value=point.min_value,
                max_value=point.max_value,
                created_at=point.created_at.isoformat(),
                updated_at=point.updated_at.isoformat()
            )
            for point in created_points
        ]
        
        return ModbusPointBatchCreateResponse(
            total=len(point_responses),
            points=point_responses
        )
        
    except ModbusControllerNotFoundException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise ServerException(f"Failed to create points: {str(e)}")

async def get_modbus_points_by_controller(controller_id: str, db: AsyncSession, point_type: str = None) -> ModbusPointListResponse:
    """Get all points for a specific controller"""
    try:
        controller_result = await db.execute(
            select(ModbusController).where(ModbusController.id == controller_id)
        )
        if not controller_result.scalar_one_or_none():
            raise ModbusControllerNotFoundException(f"Controller {controller_id} not found")
        
        query = select(ModbusPoint).where(ModbusPoint.controller_id == controller_id)
        if point_type:
            query = query.where(ModbusPoint.type == point_type)
        query = query.order_by(ModbusPoint.address.asc())
        
        result = await db.execute(query)
        points = result.scalars().all()
        
        point_list = [
            ModbusPointResponse(
                id=point.id,
                controller_id=point.controller_id,
                name=point.name,
                description=point.description,
                type=point.type,
                data_type=point.data_type,
                address=point.address,
                len=point.len,
                unit_id=point.unit_id,
                formula=point.formula,
                unit=point.unit,
                min_value=point.min_value,
                max_value=point.max_value,
                created_at=point.created_at.isoformat(),
                updated_at=point.updated_at.isoformat()
            )
            for point in points
        ]
        
        return ModbusPointListResponse(
            total=len(point_list),
            points=point_list
        )
        
    except ModbusControllerNotFoundException:
        raise
    except Exception as e:
        raise ServerException(f"Failed to get point list: {str(e)}")

async def update_modbus_point(point_id: str, request: ModbusPointUpdateRequest, db: AsyncSession) -> ModbusPointResponse:
    """Update a Modbus point"""
    try:
        result = await db.execute(
            select(ModbusPoint).where(ModbusPoint.id == point_id)
        )
        point = result.scalar_one_or_none()
        
        if not point:
            raise ModbusPointNotFoundException(f"Point {point_id} not found")
        
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.type is not None:
            update_data["type"] = request.type
        if request.data_type is not None:
            update_data["data_type"] = request.data_type
        if request.address is not None:
            update_data["address"] = request.address
        if request.len is not None:
            update_data["len"] = request.len
        if request.unit_id is not None:
            update_data["unit_id"] = request.unit_id
        if request.formula is not None:
            update_data["formula"] = request.formula
        if request.unit is not None:
            update_data["unit"] = request.unit
        if request.min_value is not None:
            update_data["min_value"] = request.min_value
        if request.max_value is not None:
            update_data["max_value"] = request.max_value
        
        if not update_data:
            raise ModbusValidationException("No data to update")
        
        update_data["updated_at"] = datetime.now()
        
        await db.execute(
            update(ModbusPoint)
            .where(ModbusPoint.id == point_id)
            .values(**update_data)
        )
        
        await db.commit()
        
        result = await db.execute(
            select(ModbusPoint).where(ModbusPoint.id == point_id)
        )
        updated_point = result.scalar_one()
        
        return ModbusPointResponse(
            id=updated_point.id,
            controller_id=updated_point.controller_id,
            name=updated_point.name,
            description=updated_point.description,
            type=updated_point.type,
            data_type=updated_point.data_type,
            address=updated_point.address,
            len=updated_point.len,
            unit_id=updated_point.unit_id,
            formula=updated_point.formula,
            unit=updated_point.unit,
            min_value=updated_point.min_value,
            max_value=updated_point.max_value,
            created_at=updated_point.created_at.isoformat(),
            updated_at=updated_point.updated_at.isoformat()
        )
        
    except (ModbusPointNotFoundException, ModbusValidationException):
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise ServerException(f"Failed to update point: {str(e)}")

async def delete_modbus_point(point_id: str, db: AsyncSession) -> bool:
    """Delete a Modbus point"""
    try:
        result = await db.execute(
            delete(ModbusPoint).where(ModbusPoint.id == point_id)
        )
        
        if result.rowcount == 0:
            raise ModbusPointNotFoundException(f"Point {point_id} not found")
        
        await db.commit()
        return True
        
    except ModbusPointNotFoundException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise ServerException(f"Failed to delete point: {str(e)}")

async def read_modbus_point_data(point_id: str, db: AsyncSession, modbus: ModbusManager) -> ModbusPointDataResponse:
    """Read data from a specific Modbus point"""
    try:
        point_result = await db.execute(
            select(ModbusPoint).where(ModbusPoint.id == point_id)
        )
        point = point_result.scalar_one_or_none()
        
        if not point:
            raise ModbusPointNotFoundException(f"Point {point_id} not found")
        
        controller_result = await db.execute(
            select(ModbusController).where(ModbusController.id == point.controller_id)
        )
        controller = controller_result.scalar_one_or_none()
        
        if not controller:
            raise ModbusControllerNotFoundException(f"Controller {point.controller_id} not found")
        
        data_result = await modbus.read_point_data(
            host=controller.host,
            port=controller.port,
            point_type=point.type,
            address=point.address,
            length=point.len,
            unit_id=point.unit_id,
            data_type=point.data_type,
            formula=point.formula,
            min_value=point.min_value,
            max_value=point.max_value
        )
        
        return ModbusPointDataResponse(
            point_id=point.id,
            point_name=point.name,
            controller_name=controller.name,
            raw_data=data_result["raw_data"],
            converted_value=data_result["converted_value"],
            final_value=data_result["final_value"],
            data_type=data_result["data_type"],
            unit=point.unit,
            formula=point.formula,
            read_time=data_result["read_time"],
            range_valid=data_result["range_valid"],
            range_message=data_result["range_message"],
            min_value=data_result["min_value"],
            max_value=data_result["max_value"]
        )
        
    except (ModbusPointNotFoundException, ModbusControllerNotFoundException):
        raise
    except Exception as e:
        raise ModbusReadException(f"Failed to read point data: {str(e)}")

async def read_modbus_controller_points_data(controller_id: str, db: AsyncSession, modbus: ModbusManager, point_type: str = None) -> ModbusControllerValuesResponse:
    """Read values from all points of a controller (simplified response)"""
    try:
        controller_result = await db.execute(
            select(ModbusController).where(ModbusController.id == controller_id)
        )
        controller = controller_result.scalar_one_or_none()
        
        if not controller:
            raise ModbusControllerNotFoundException(f"Controller {controller_id} not found")
        
        query = select(ModbusPoint).where(ModbusPoint.controller_id == controller_id)
        if point_type:
            query = query.where(ModbusPoint.type == point_type)
        query = query.order_by(ModbusPoint.address.asc())
        
        points_result = await db.execute(query)
        points = points_result.scalars().all()
        
        if not points:
            raise ModbusValidationException(f"No points found for controller {controller_id}")
        
        successful_values = []
        failed_count = 0
        
        for point in points:
            try:
                data_result = await modbus.read_point_data(
                    host=controller.host,
                    port=controller.port,
                    point_type=point.type,
                    address=point.address,
                    length=point.len,
                    unit_id=point.unit_id,
                    data_type=point.data_type,
                    formula=point.formula,
                    min_value=point.min_value,
                    max_value=point.max_value
                )
                
                point_value = ModbusPointValueResponse(
                    name=point.name,
                    value=data_result["final_value"]
                )
                
                successful_values.append(point_value)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to read point {point.name}: {e}")
        
        return ModbusControllerValuesResponse(
            total=len(points),
            successful=len(successful_values),
            failed=failed_count,
            values=successful_values
        )
        
    except (ModbusControllerNotFoundException, ModbusValidationException):
        raise
    except Exception as e:
        raise ModbusReadException(f"Failed to read controller points data: {str(e)}")

async def write_modbus_point_data(point_id: str, request: ModbusPointWriteRequest, db: AsyncSession, modbus: ModbusManager) -> ModbusPointWriteResponse:
    """Write data to a specific Modbus point"""
    try:
        point_result = await db.execute(
            select(ModbusPoint).where(ModbusPoint.id == point_id)
        )
        point = point_result.scalar_one_or_none()
        
        if not point:
            raise ModbusPointNotFoundException(f"Point {point_id} not found")
        
        controller_result = await db.execute(
            select(ModbusController).where(ModbusController.id == point.controller_id)
        )
        controller = controller_result.scalar_one_or_none()
        
        if not controller:
            raise ModbusControllerNotFoundException(f"Controller {point.controller_id} not found")
        
        if point.type not in ["coil", "holding_register"]:
            raise ModbusValidationException(f"Point type {point.type} does not support writing")
        
        if point.type == "coil" and not isinstance(request.value, bool):
            raise ModbusValidationException(f"Coil requires boolean value, got {type(request.value)}")
        
        if point.type == "holding_register" and not isinstance(request.value, (int, float)):
            raise ModbusValidationException(f"Holding register requires numeric value, got {type(request.value)}")
        
        data_result = await modbus.write_point_data(
            host=controller.host,
            port=controller.port,
            point_type=point.type,
            address=point.address,
            value=request.value,
            unit_id=request.unit_id or point.unit_id,
            data_type=point.data_type,
            formula=point.formula,
            min_value=point.min_value,
            max_value=point.max_value
        )
        
        return ModbusPointWriteResponse(
            point_id=point.id,
            point_name=point.name,
            controller_name=controller.name,
            write_value=data_result["write_value"],
            raw_data=data_result["raw_data"],
            write_time=data_result["write_time"],
            success=data_result["success"]
        )
        
    except (ModbusPointNotFoundException, ModbusControllerNotFoundException, ModbusValidationException, ModbusWriteException, ModbusRangeValidationException):
        raise
    except Exception as e:
        raise ModbusWriteException(f"Failed to write point data: {str(e)}")

# ===== Configuration Import/Export Services =====

async def export_modbus_controller_config_file(
    controller_id: str, 
    format: ConfigFormat, 
    db: AsyncSession
) -> Dict[str, str]:
    """Export controller configuration as file"""
    try:
        # First get controller information to get the name
        controller_result = await db.execute(
            select(ModbusController).where(ModbusController.id == controller_id)
        )
        controller = controller_result.scalar_one_or_none()
        
        if not controller:
            raise ModbusControllerNotFoundException(f"Controller {controller_id} not found")
        
        manager = ModbusConfigManager()
        config = await manager.export_config(controller_id, db, format)
        
        safe_controller_name = "".join(c for c in controller.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_controller_name = safe_controller_name.replace(' ', '_')
        
        filename = f"modbus_{safe_controller_name}_{format.value}.json"
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        # Write JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return {
            "file_path": file_path,
            "filename": filename,
            "controller_id": controller_id,
            "controller_name": controller.name,
            "format": format.value,
            "export_time": datetime.now().isoformat()
        }
        
    except ModbusControllerNotFoundException:
        raise
    except ModbusConfigException:
        raise
    except Exception as e:
        raise ServerException(f"Failed to export configuration: {str(e)}")

async def import_modbus_configuration_from_file(
    config: Dict[str, Any], 
    format: ConfigFormat, 
    db: AsyncSession
) -> ModbusConfigImportResponse:
    """Import configuration from file"""
    try:
        controllers = await import_modbus_config(config, db, format.value)
        
        # Calculate total points
        total_points = 0
        for controller in controllers:
            points = await get_modbus_points_by_controller(controller.id, db)
            total_points += points.total
        
        return ModbusConfigImportResponse(
            imported_controllers=[ctrl.id for ctrl in controllers],
            total_points=total_points,
            import_time=datetime.now().isoformat()
        )
        
    except (ModbusConfigException, ModbusConfigFormatMismatchException):
        raise
    except Exception as e:
        raise ServerException(f"Failed to import configuration: {str(e)}")

async def validate_modbus_configuration_from_file(
    config: Dict[str, Any], 
    format: ConfigFormat
) -> ModbusConfigValidationResponse:
    """Validate configuration file"""
    try:
        validation_result = validate_modbus_config(config, format.value)
        
        return ModbusConfigValidationResponse(
            is_valid=validation_result.is_valid,
            errors=validation_result.errors,
            warnings=validation_result.warnings
        )
        
    except (ModbusConfigException, ModbusConfigFormatMismatchException):
        raise
    except Exception as e:
        raise ServerException(f"Failed to validate configuration: {str(e)}")