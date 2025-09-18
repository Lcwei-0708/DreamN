import logging
from typing import Dict, Any
from datetime import datetime
from extensions.modbus import ModbusManager
from models.modbus_point import ModbusPoint
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models.modbus_controller import ModbusController
from utils.modbus import (
    export_modbus_config, import_modbus_config, ImportMode
)
from .schema import (
    ModbusControllerCreateRequest, ModbusControllerUpdateRequest, ModbusControllerResponse,
    ModbusControllerListResponse, ModbusControllerDeleteRequest, ModbusControllerDeleteResponse,
    ModbusPointBatchCreateRequest, ModbusPointUpdateRequest, ModbusPointResponse, ModbusPointListResponse,
    ModbusPointDeleteRequest, ModbusPointDeleteResponse, ModbusPointDataResponse, ModbusPointValueResponse,
    ModbusPointWriteRequest, ModbusPointWriteResponse,
    ModbusPointBatchCreateResponseInternal, ModbusPointBatchCreateResult,
    ModbusControllerValuesResponse,
    ModbusConfigImportResponseInternal, ModbusPointImportResult,
    ImportMode
)
from utils.custom_exception import (
    ServerException, ModbusConnectionException, ModbusControllerNotFoundException,
    ModbusPointNotFoundException, ModbusReadException, ModbusValidationException, 
    ModbusWriteException, ModbusRangeValidationException, ModbusConfigException,
    ModbusControllerDuplicateException, ModbusPointDuplicateException, ModbusConfigFormatException
)

logger = logging.getLogger(__name__)

async def create_modbus_controller(request: ModbusControllerCreateRequest, db: AsyncSession, modbus: ModbusManager) -> ModbusControllerResponse:
    """Create Modbus controller (test connection first)"""
    try:
        # Check if controller with same host and port already exists
        existing_controller = await db.execute(
            select(ModbusController).where(
                ModbusController.host == request.host,
                ModbusController.port == request.port
            )
        )
        
        if existing_controller.scalar_one_or_none():
            raise ModbusControllerDuplicateException(
                f"Controller with host {request.host} and port {request.port} already exists"
            )
        
        # Create controller first
        controller = ModbusController(
            name=request.name,
            host=request.host,
            port=request.port,
            timeout=request.timeout,
            status=False  # Set initial status as False
        )
        
        db.add(controller)
        await db.commit()
        await db.refresh(controller)
        
        # Try to test connection (but don't fail if it doesn't work)
        try:
            test_client_id = modbus.create_tcp(
                host=request.host,
                port=request.port,
                timeout=request.timeout
            )
            
            success = await modbus.connect(test_client_id)
            
            modbus.disconnect(test_client_id)
            del modbus.clients[test_client_id]
            
            # Update status based on connection test result
            if success:
                controller.status = True
                await db.commit()
                await db.refresh(controller)
            else:
                logger.warning(f"Controller {controller.name} connection test failed, but controller was created")
                
        except Exception as e:
            logger.warning(f"Controller {controller.name} connection test failed: {e}, but controller was created")
        
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
    except ModbusControllerDuplicateException:
        raise
    except Exception as e:
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
        
        # Check if another controller with same host and port already exists (excluding current controller)
        if request.host is not None or request.port is not None:
            existing_controller = await db.execute(
                select(ModbusController).where(
                    ModbusController.host == new_host,
                    ModbusController.port == new_port,
                    ModbusController.id != controller_id
                )
            )
            
            if existing_controller.scalar_one_or_none():
                raise ModbusControllerDuplicateException(
                    f"Another controller with host {new_host} and port {new_port} already exists"
                )
        
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
        
    except ModbusConnectionException:
        raise
    except ModbusControllerNotFoundException:
        raise
    except ModbusControllerDuplicateException:
        raise
    except Exception as e:
        raise ServerException(f"Failed to update controller: {str(e)}")

async def delete_modbus_controllers(
    request: ModbusControllerDeleteRequest, 
    db: AsyncSession
) -> ModbusControllerDeleteResponse:
    """Delete multiple Modbus controllers (clear related points)"""
    results = []
    
    for controller_id in request.controller_ids:
        try:
            await db.execute(
                delete(ModbusPoint).where(ModbusPoint.controller_id == controller_id)
            )
            
            result = await db.execute(
                delete(ModbusController).where(ModbusController.id == controller_id)
            )
            
            if result.rowcount > 0:
                results.append({
                    "id": controller_id,
                    "status": "success",
                    "message": "Deleted Successfully"
                })
            else:
                results.append({
                    "id": controller_id,
                    "status": "not_found",
                    "message": "Controller not found"
                })
                
        except Exception as e:
            results.append({
                "id": controller_id,
                "status": "error",
                "message": "Server error"
            })
    
    await db.commit()
    
    deleted_count = len([r for r in results if r["status"] == "success"])
    failed_count = len([r for r in results if r["status"] != "success"])
    
    return ModbusControllerDeleteResponse(
        total_requested=len(request.controller_ids),
        deleted_count=deleted_count,
        failed_count=failed_count,
        results=results
    )

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
        
        response_time = (end_time - start_time).total_seconds() * 1000
        
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

async def create_modbus_points_batch(
    request: ModbusPointBatchCreateRequest, 
    db: AsyncSession
) -> ModbusPointBatchCreateResponseInternal:
    """Create multiple Modbus points for a controller"""
    try:
        # Verify controller exists
        controller_result = await db.execute(
            select(ModbusController).where(ModbusController.id == request.controller_id)
        )
        if not controller_result.scalar_one_or_none():
            raise ModbusControllerNotFoundException(f"Controller {request.controller_id} not found")
        
        results = []
        success_count = 0
        skipped_count = 0
        failed_count = 0
        
        for point_request in request.points:
            try:
                # Check for existing point with same key fields
                existing_point = await db.execute(
                    select(ModbusPoint).where(
                        ModbusPoint.controller_id == request.controller_id,
                        ModbusPoint.address == point_request.address,
                        ModbusPoint.type == point_request.type,
                        ModbusPoint.unit_id == point_request.unit_id
                    )
                )
                
                if existing_point.scalar_one_or_none():
                    # Skip duplicate point
                    results.append(ModbusPointBatchCreateResult(
                        point_id=None,
                        name=point_request.name,
                        status="skipped",
                        message="Point already exists"
                    ))
                    skipped_count += 1
                else:
                    # Create new point
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
                    await db.commit()
                    await db.refresh(point)
                    
                    results.append(ModbusPointBatchCreateResult(
                        point_id=point.id,
                        name=point.name,
                        status="success",
                        message="Created successfully"
                    ))
                    success_count += 1
                    
            except Exception as e:
                results.append(ModbusPointBatchCreateResult(
                    point_id=None,
                    name=point_request.name,
                    status="failed",
                    message=str(e)
                ))
                failed_count += 1
        
        return ModbusPointBatchCreateResponseInternal(
            results=results,
            total_requested=len(request.points),
            success_count=success_count,
            skipped_count=skipped_count,
            failed_count=failed_count
        )
        
    except ModbusControllerNotFoundException:
        raise
    except Exception as e:
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

async def update_modbus_point(
    point_id: str, 
    request: ModbusPointUpdateRequest, 
    db: AsyncSession
) -> ModbusPointResponse:
    """Update a Modbus point"""
    try:
        point_result = await db.execute(
            select(ModbusPoint).where(ModbusPoint.id == point_id)
        )
        point = point_result.scalar_one_or_none()
        
        if not point:
            raise ModbusPointNotFoundException(f"Point {point_id} not found")
        
        # Check for duplicates
        new_address = request.address if request.address is not None else point.address
        new_type = request.type if request.type is not None else point.type
        new_unit_id = request.unit_id if request.unit_id is not None else point.unit_id
        
        existing_point = await db.execute(
            select(ModbusPoint).where(
                ModbusPoint.controller_id == point.controller_id,
                ModbusPoint.address == new_address,
                ModbusPoint.type == new_type,
                ModbusPoint.unit_id == new_unit_id,
                ModbusPoint.id != point_id
            )
        )
        
        if existing_point.scalar_one_or_none():
            raise ModbusPointDuplicateException(
                f"Point with controller_id={point.controller_id}, address={new_address}, "
                f"type={new_type}, unit_id={new_unit_id} already exists"
            )
        
        # Update point attributes
        update_data = request.dict(exclude_unset=True)
        if update_data:
            await db.execute(
                update(ModbusPoint)
                .where(ModbusPoint.id == point_id)
                .values(**update_data)
            )
            await db.commit()
            
            # Refresh the point
            await db.refresh(point)
        
        # Convert to ModbusPointResponse
        return ModbusPointResponse(
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
        
    except ModbusPointNotFoundException:
        raise
    except ModbusPointDuplicateException:
        raise
    except Exception as e:
        raise ServerException(f"Failed to update point: {str(e)}")

async def delete_modbus_points(
    request: ModbusPointDeleteRequest, 
    db: AsyncSession
) -> ModbusPointDeleteResponse:
    """Delete multiple Modbus points"""
    results = []
    
    for point_id in request.point_ids:
        try:
            result = await db.execute(
                delete(ModbusPoint).where(ModbusPoint.id == point_id)
            )
            
            if result.rowcount > 0:
                results.append({
                    "id": point_id,
                    "status": "success",
                    "message": "Deleted Successfully"
                })
            else:
                results.append({
                    "id": point_id,
                    "status": "not_found",
                    "message": "Point not found"
                })
                
        except Exception as e:
            results.append({
                "id": point_id,
                "status": "error",
                "message": "Server error"
            })
    
    await db.commit()
    
    deleted_count = len([r for r in results if r["status"] == "success"])
    failed_count = len([r for r in results if r["status"] != "success"])
    
    return ModbusPointDeleteResponse(
        total_requested=len(request.point_ids),
        deleted_count=deleted_count,
        failed_count=failed_count,
        results=results
    )

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

async def read_modbus_controller_points_data(controller_id: str, db: AsyncSession, modbus: ModbusManager, point_type: str = None, convert: bool = True) -> ModbusControllerValuesResponse:
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
            return ModbusControllerValuesResponse(
                total=0,
                successful=0,
                failed=0,
                values=[]
            )
        
        successful_values = []
        failed_count = 0
        
        for point in points:
            try:
                if convert:
                    # Use original conversion logic
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
                    final_value = data_result["final_value"]
                else:
                    # No conversion, read raw data directly
                    raw_data = await modbus.read_modbus_data(
                        client_id=modbus.ensure_controller_client(controller.id, controller.host, controller.port, controller.timeout),
                        point_type=point.type,
                        address=point.address,
                        count=point.len,
                        unit_id=point.unit_id
                    )
                    # If single value, take first; if multiple values, keep as list
                    final_value = raw_data[0] if len(raw_data) == 1 else raw_data
                
                point_value = ModbusPointValueResponse(
                    point_id=point.id,
                    point_name=point.name,
                    value=final_value,
                    unit=point.unit,
                    timestamp=datetime.now().isoformat()
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
        
    except ModbusControllerNotFoundException:
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

async def import_modbus_configuration_from_file(
    config: Dict[str, Any], 
    format: str, 
    db: AsyncSession, 
    import_mode: ImportMode
) -> ModbusConfigImportResponseInternal:
    """
    Import Modbus configuration from file (single controller only)
        
    Status Descriptions:
        - success: Controller and points created/updated successfully
        - skipped_controller: Controller already exists and skip mode is used
        - skipped_points: All points already exist and were skipped
        - partial_success: Controller successful, but some points failed or skipped
        - controller_failed: Controller import failed
        - points_failed: Controller successful but all points import failed
    """
    try:
        result = await import_modbus_config(config, db, format, import_mode.value)
        
        controller_result = result["controller_result"]
        
        points = controller_result["points"]
        total_points = len(points)
        success_count = sum(1 for p in points if p["status"] == "success")
        skipped_count = sum(1 for p in points if p["status"] == "skipped")
        failed_count = sum(1 for p in points if p["status"] in ["failed", "invalid", "error"])

        response = ModbusConfigImportResponseInternal(
            controller_id=controller_result.get("controller_id"),
            controller_name=controller_result["controller_name"],
            points=[
                ModbusPointImportResult(
                    point_id=p.get("point_id"),
                    point_name=p["point_name"],
                    status=p["status"],
                    message=p["message"]
                ) for p in controller_result["points"]
            ],
            total_points=total_points,
            success_count=success_count,
            skipped_count=skipped_count,
            failed_count=failed_count
        )
        
        response._status = controller_result["status"]
        response._message = controller_result["message"]
        
        if controller_result["status"] == "skipped":
            # Controller was skipped
            if import_mode == ImportMode.SKIP_CONTROLLER:
                # Skip mode: Controller already exists, normal skip
                response._status = "skipped_controller"
                response._message = "Controller already exists"
            else:
                # Skip in other modes is considered a failure
                response._status = "controller_failed"
                response._message = "Controller import failed"
        elif success_count == 0:
            # No points were successfully imported
            if skipped_count == total_points and failed_count == 0:
                # All points were skipped (already exist)
                response._status = "skipped_points"
                response._message = "All points already exists"
            elif failed_count == total_points and skipped_count == 0:
                # All points failed
                if controller_result["status"] == "success":
                    # Controller successful but all points failed
                    response._status = "points_failed"
                    response._message = "All points failed to import"
                else:
                    # Controller also failed
                    response._status = "controller_failed"
                    response._message = "Controller failed to import"
            else:
                # Mixed case: some skipped, some failed, but no success
                if controller_result["status"] == "success":
                    # Controller successful but all points failed or skipped
                    response._status = "points_failed"
                    response._message = "All points failed to import"
                else:
                    # Controller also failed
                    response._status = "controller_failed"
                    response._message = "Controller failed to import"
        elif success_count > 0 and (skipped_count > 0 or failed_count > 0):
            # Partial success: Some points succeeded, but some were skipped or failed
            response._status = "partial_success"
            response._message = "Controller imported with partial success"
        else:
            # All points succeeded
            response._status = "success"
            response._message = "Controller imported successfully"
        
        return response
    except ModbusConfigFormatException:
        raise
    except ModbusConfigException:
        raise
    except Exception as e:
        raise ServerException(f"Import failed: {str(e)}")

async def export_modbus_controller_config_data(
    controller_id: str, 
    format: str, 
    db: AsyncSession
) -> Dict[str, Any]:
    """Export Modbus controller configuration data"""
    try:
        controller_result = await db.execute(
            select(ModbusController).where(ModbusController.id == controller_id)
        )
        controller = controller_result.scalar_one_or_none()
        if not controller:
            raise ModbusControllerNotFoundException(f"Controller {controller_id} not found")
        
        config = await export_modbus_config(controller_id, db, format)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"modbus_{controller.name}_{format}_{timestamp}.json"
        
        return {
            "config_data": config,
            "filename": filename,
            "controller_name": controller.name,
            "format": format
        }
        
    except ModbusControllerNotFoundException:
        raise
    except Exception as e:
        raise ModbusConfigException(f"Export failed: {str(e)}")

async def delete_all_modbus_points_by_controller_id(controller_id: str, db: AsyncSession) -> None:
    """Delete all points for a specific controller"""
    await db.execute(
        delete(ModbusPoint).where(ModbusPoint.controller_id == controller_id)
    )
    await db.commit()