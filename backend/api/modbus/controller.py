import json
from typing import Annotated, List, Optional, Dict, Any, Union
from core.dependencies import get_db
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from extensions.modbus import get_modbus, ModbusManager
from utils.response import APIResponse, parse_responses, common_responses
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, Body
from utils.custom_exception import (
    ModbusConnectionException, ModbusControllerNotFoundException,
    ModbusPointNotFoundException, ModbusReadException, ModbusValidationException,
    ModbusWriteException, ModbusRangeValidationException,
    ModbusConfigException, ModbusConfigFormatMismatchException,
    ModbusControllerDuplicateException, ModbusPointDuplicateException,
    ServerException
)
from .services import (
    create_modbus_controller, get_modbus_controllers, update_modbus_controller, delete_modbus_controllers,
    test_modbus_controller, create_modbus_points_batch, get_modbus_points_by_controller,
    update_modbus_point, delete_modbus_points, read_modbus_controller_points_data,
    write_modbus_point_data,
    export_modbus_controller_config_file, import_modbus_configuration_from_file,
    validate_modbus_configuration_from_file
)
from .schema import (
    ModbusControllerCreateRequest, ModbusControllerUpdateRequest, ModbusControllerResponse,
    ModbusControllerListResponse, ModbusPointBatchCreateRequest, ModbusPointUpdateRequest,
    ModbusPointResponse, ModbusPointListResponse, ModbusPointBatchCreateResponse,
    ModbusControllerValuesResponse, ModbusPointWriteRequest, ModbusPointWriteResponse,
    ModbusConfigImportResponse, ModbusConfigValidationResponse, ModbusConfigExportRequest,
    modbus_controller_response_example, modbus_controller_list_response_example,
    modbus_point_response_example, modbus_point_list_response_example,
    modbus_multi_point_data_response_example,
    modbus_point_write_response_example,
    modbus_point_batch_create_response_example,
    modbus_config_import_response_example,
    ModbusControllerDeleteRequest, ModbusPointDeleteRequest,
    ModbusControllerDeleteResponse, ModbusPointDeleteResponse,
    ModbusControllerDeleteFailedResponse, ModbusPointDeleteFailedResponse,
    modbus_controller_delete_response_example, modbus_point_delete_response_example,
    modbus_controller_delete_failed_response_example, modbus_point_delete_failed_response_example,
    PointType, ConfigFormat
)

router = APIRouter(tags=["modbus"])

@router.post(
    "/controllers",
    response_model=APIResponse[ModbusControllerResponse],
    response_model_exclude_unset=True,
    summary="Create Modbus controller",
    responses=parse_responses({
        200: ("Controller created successfully", ModbusControllerResponse, modbus_controller_response_example),
        409: ("Controller already exists", None)
    }, default=common_responses)
)
async def create_controller(
    payload: ModbusControllerCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    modbus: Annotated[ModbusManager, Depends(get_modbus)]
):
    try:
        result = await create_modbus_controller(payload, db, modbus)
        return APIResponse(code=200, message="Controller created successfully", data=result)
    except ModbusControllerDuplicateException:
        raise HTTPException(status_code=409, detail="Controller already exists")
    except Exception:
        raise HTTPException(status_code=500)

@router.get(
    "/controllers",
    response_model=APIResponse[ModbusControllerListResponse],
    response_model_exclude_unset=True,
    summary="Get Modbus controller list",
    responses=parse_responses({
        200: ("Get controller list successfully", ModbusControllerListResponse, modbus_controller_list_response_example)
    }, default=common_responses)
)
async def get_controllers(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: bool = Query(None, description="Filter by controller status (true=connected, false=disconnected)"),
    name: str = Query(None, description="Search by controller name (partial match)")
):
    try:
        data = await get_modbus_controllers(db, status=status, name=name)
        return APIResponse(code=200, message="Get controller list successfully", data=data)
    except Exception:
        raise HTTPException(status_code=500)

@router.put(
    "/controllers/{controller_id}",
    response_model=APIResponse[ModbusControllerResponse],
    response_model_exclude_unset=True,
    summary="Update Modbus controller",
    responses=parse_responses({
        200: ("Controller updated successfully", ModbusControllerResponse),
        404: ("Controller not found", None),
        409: ("Controller already exists", None)
    }, default=common_responses)
)
async def update_controller(
    controller_id: str,
    payload: ModbusControllerUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    modbus: Annotated[ModbusManager, Depends(get_modbus)]
):
    try:
        result = await update_modbus_controller(controller_id, payload, db, modbus)
        return APIResponse(code=200, message="Controller updated successfully", data=result)
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except ModbusControllerDuplicateException:
        raise HTTPException(status_code=409, detail="Controller already exists")
    except Exception:
        raise HTTPException(status_code=500)

@router.delete(
    "/controllers",
    response_model=APIResponse[Union[None, ModbusControllerDeleteResponse, ModbusControllerDeleteFailedResponse]],
    response_model_exclude_unset=True,
    summary="Delete Modbus controllers (clear related points)",
    responses=parse_responses({
        200: ("All controllers deleted successfully", None),
        207: ("Delete controllers partial success", ModbusControllerDeleteResponse, modbus_controller_delete_response_example),
        400: ("All controllers failed to delete", ModbusControllerDeleteFailedResponse, modbus_controller_delete_failed_response_example)
    }, default=common_responses)
)
async def delete_controllers(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: ModbusControllerDeleteRequest = Body(...)
):
    """Delete multiple Modbus controllers. Related points will be deleted automatically."""
    try:
        result = await delete_modbus_controllers(request, db)
        
        if result.failed_count == 0:
            # All success
            return APIResponse(code=200, message="All controllers deleted successfully")
        elif result.deleted_count == 0:
            # All failed
            failed_results = [r for r in result.results if r.status != "success"]
            response_data = APIResponse(
                code=400, 
                message="All controllers failed to delete", 
                data=ModbusControllerDeleteFailedResponse(results=failed_results)
            )
            raise HTTPException(status_code=400, detail=response_data.dict(exclude_none=True))
        else:
            # Partial success, partial failed
            response_data = APIResponse(
                code=207, 
                message="Delete controllers partial success", 
                data=result
            )
            raise HTTPException(status_code=207, detail=response_data.dict(exclude_none=True))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/controllers/test",
    response_model=APIResponse[dict],
    response_model_exclude_unset=True,
    summary="Test Modbus controller connection (do not save to database)",
    responses=parse_responses({
        200: ("Controller test successful", dict),
        400: ("Controller test failed", None)
    }, default=common_responses)
)
async def test_controller(
    payload: ModbusControllerCreateRequest,
    modbus: Annotated[ModbusManager, Depends(get_modbus)]
):
    try:
        result = await test_modbus_controller(payload, modbus)
        return APIResponse(code=200, message="Controller test successful", data=result)
    except ModbusConnectionException:
        raise HTTPException(status_code=400, detail="Controller test failed")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/points/batch",
    response_model=APIResponse[ModbusPointBatchCreateResponse],
    response_model_exclude_unset=True,
    summary="Create multiple Modbus points for a controller (duplicates will be skipped)",
    responses=parse_responses({
        200: ("Points created successfully", ModbusPointBatchCreateResponse, modbus_point_batch_create_response_example),
        404: ("Controller not found", None)
    }, default=common_responses)
)
async def create_points_batch(
    request: ModbusPointBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Create multiple Modbus points for a controller. Duplicate points (same controller_id, address, type, unit_id) will be skipped."""
    try:
        result = await create_modbus_points_batch(request, db)
        
        message = f"Successfully created {result['created_count']} points"
        if result['skipped_count'] > 0:
            message += f", skipped {result['skipped_count']} duplicate points"
        
        return APIResponse(code=200, message=message, data=result)
    except ModbusControllerNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500)

@router.get(
    "/controllers/{controller_id}/points",
    response_model=APIResponse[ModbusPointListResponse],
    response_model_exclude_unset=True,
    summary="Get all points for a specific controller",
    responses=parse_responses({
        200: ("Get point list successfully", ModbusPointListResponse, modbus_point_list_response_example),
        404: ("Controller not found", None)
    }, default=common_responses)
)
async def get_points_by_controller(
    controller_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    point_type: PointType = Query(None, description="Filter by point type (coil/input/holding_register/input_register)")
):
    try:
        data = await get_modbus_points_by_controller(controller_id, db, point_type=point_type)
        return APIResponse(code=200, message="Get point list successfully", data=data)
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.put(
    "/points/{point_id}",
    response_model=APIResponse[ModbusPointResponse],
    response_model_exclude_unset=True,
    summary="Update a Modbus point",
    responses=parse_responses({
        200: ("Point updated successfully", ModbusPointResponse, modbus_point_response_example),
        400: ("No data to update", None),
        404: ("Point not found", None),
        409: ("Point already exists", None)
    }, default=common_responses)
)
async def update_point(
    db: Annotated[AsyncSession, Depends(get_db)],
    point_id: str,
    request: ModbusPointUpdateRequest,
):
    """Update a Modbus point"""
    try:
        point = await update_modbus_point(point_id, request, db)
        return APIResponse(code=200, message="Point updated successfully", data=point)
    except ModbusPointNotFoundException:
        raise HTTPException(status_code=404, detail="Point not found")
    except ModbusPointDuplicateException:
        raise HTTPException(status_code=409, detail="Point already exists")
    except Exception:
        raise HTTPException(status_code=500)

@router.delete(
    "/points",
    response_model=APIResponse[Union[None, ModbusPointDeleteResponse, ModbusPointDeleteFailedResponse]],
    response_model_exclude_unset=True,
    summary="Delete Modbus points",
    responses=parse_responses({
        200: ("All points deleted successfully", None),
        207: ("Delete points partial success", ModbusPointDeleteResponse, modbus_point_delete_response_example),
        400: ("All points failed to delete", ModbusPointDeleteFailedResponse, modbus_point_delete_failed_response_example)
    }, default=common_responses)
)
async def delete_points(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: ModbusPointDeleteRequest = Body(...)
):
    """Delete multiple Modbus points"""
    try:
        result = await delete_modbus_points(request, db)
        
        if result.failed_count == 0:
            # All success
            return APIResponse(code=200, message="All points deleted successfully")
        elif result.deleted_count == 0:
            # All failed
            failed_results = [r for r in result.results if r.status != "success"]
            response_data = APIResponse(
                code=400, 
                message="All points failed to delete", 
                data=ModbusPointDeleteFailedResponse(results=failed_results)
            )
            raise HTTPException(status_code=400, detail=response_data.dict(exclude_none=True))
        else:
            # Partial success, partial failed
            response_data = APIResponse(
                code=207, 
                message="Delete points partial success", 
                data=result
            )
            raise HTTPException(status_code=207, detail=response_data.dict(exclude_none=True))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500)

@router.get(
    "/controllers/{controller_id}/points/data",
    response_model=APIResponse[ModbusControllerValuesResponse],
    response_model_exclude_unset=True,
    summary="Read values from all points of a controller",
    responses=parse_responses({
        200: ("Controller values read successfully", ModbusControllerValuesResponse, modbus_multi_point_data_response_example),
        400: ("Controller not connected or read failed", None),
        404: ("Controller not found", None)
    }, default=common_responses)
)
async def read_controller_points_data(
    controller_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    modbus: Annotated[ModbusManager, Depends(get_modbus)],
    point_type: PointType = Query(None, description="Filter by point type (coil/input/holding_register/input_register)"),
    convert: bool = Query(True, description="是否要進行資料轉換（預設為 true）")
):
    try:
        result = await read_modbus_controller_points_data(controller_id, db, modbus, point_type=point_type, convert=convert)
        return APIResponse(code=200, message="Controller values read successfully", data=result)
    except ModbusValidationException:
        raise HTTPException(status_code=400, detail="Controller not connected or read failed")
    except ModbusReadException:
        raise HTTPException(status_code=400, detail="Controller not connected or read failed")
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/points/{point_id}/write",
    response_model=APIResponse[ModbusPointWriteResponse],
    response_model_exclude_unset=True,
    summary="Write data to a specific Modbus point",
    responses=parse_responses({
        200: ("Point data written successfully", ModbusPointWriteResponse, modbus_point_write_response_example),
        400: ("Point does not support writing or validation failed", None),
        404: ("Point not found", None)
    }, default=common_responses)
)
async def write_point_data(
    point_id: str,
    payload: ModbusPointWriteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    modbus: Annotated[ModbusManager, Depends(get_modbus)]
):
    try:
        result = await write_modbus_point_data(point_id, payload, db, modbus)
        return APIResponse(code=200, message="Point data written successfully", data=result)
    except ModbusWriteException:
        raise HTTPException(status_code=400, detail="Write operation failed")
    except ModbusPointNotFoundException:
        raise HTTPException(status_code=404, detail="Point not found")
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except ModbusValidationException:
        raise HTTPException(status_code=409, detail="Point does not support writing or validation failed")
    except ModbusRangeValidationException:
        raise HTTPException(status_code=422, detail="Value is outside the valid range")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/config/import",
    response_model=APIResponse[ModbusConfigImportResponse],
    response_model_exclude_unset=True,
    summary="Import Modbus Configuration",
    responses=parse_responses({
        200: ("Configuration imported successfully", ModbusConfigImportResponse, modbus_config_import_response_example),
        400: ("Import failed / Invalid JSON format / Only JSON files are supported", None),
        422: ("Configuration format does not match the selected format", None)
    }, default=common_responses)
)
async def import_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(..., description="配置文件 (JSON 格式)"),
    format: ConfigFormat = Form(ConfigFormat.native, description="導入格式"),
    overwrite: bool = Form(False, description="是否覆蓋現有的 controller 和 point")
):
    """Import configuration from file"""
    try:
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are supported")
        
        content = await file.read()
        try:
            config = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        result = await import_modbus_configuration_from_file(config, format, db, overwrite)
        
        message = f"Successfully imported {result.imported_count} controllers"
        if result.skipped_count > 0:
            message += f", skipped {result.skipped_count} duplicate controllers"
        
        return APIResponse(code=200, message=message, data=result)
    except ModbusConfigException:
        raise HTTPException(status_code=400, detail="Import failed")
    except ModbusConfigFormatMismatchException:
        raise HTTPException(status_code=422, detail="Configuration format does not match the selected format")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/controllers/export",
    summary="Export Modbus Controller Configuration",
    responses=parse_responses({
        200: ("Configuration exported successfully", None),
        400: ("Export failed", None),
        404: ("Controller not found", None)
    }, default=common_responses)
)
async def export_controller_config(
    payload: ModbusConfigExportRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Export controller configuration as file"""
    try:
        result = await export_modbus_controller_config_file(payload.controller_ids, payload.format, db)
        
        # Return file download
        return FileResponse(
            path=result["file_path"],
            filename=result["filename"],
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={result['filename']}"
            }
        )
    except ModbusConfigException:
        raise HTTPException(status_code=400, detail="Export failed")
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except Exception:
        raise HTTPException(status_code=500)
    
@router.post(
    "/config/validate",
    response_model=APIResponse[ModbusConfigValidationResponse],
    response_model_exclude_unset=True,
    summary="Validate Modbus Configuration",
    responses=parse_responses({
        200: ("Configuration validation completed", ModbusConfigValidationResponse),
        400: ("Invalid JSON format / Only JSON files are supported", None),
        422: ("Configuration format does not match the selected format", None)
    }, default=common_responses)
)
async def validate_config(
    file: UploadFile = File(..., description="配置文件 (JSON 格式)"),
    format: ConfigFormat = Form(ConfigFormat.native, description="導入格式")
):
    """Validate configuration file"""
    try:
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are supported")
        
        content = await file.read()
        try:
            config = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        result = await validate_modbus_configuration_from_file(config, format)
        return APIResponse(code=200, message="Configuration validation completed", data=result)
    except ModbusConfigFormatMismatchException:
        raise HTTPException(status_code=422, detail="Configuration format does not match the selected format")
    except Exception:
        raise HTTPException(status_code=500)