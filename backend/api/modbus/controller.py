import json
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_db
from extensions.modbus import get_modbus, ModbusManager
from utils.response import APIResponse, parse_responses, common_responses
from utils.custom_exception import (
    ServerException, ModbusConnectionException, ModbusControllerNotFoundException,
    ModbusPointNotFoundException, ModbusReadException, ModbusValidationException,
    ModbusWriteException, ModbusRangeValidationException,
    ModbusConfigException, ModbusConfigFormatMismatchException
)
from .services import (
    create_modbus_controller, get_modbus_controllers, update_modbus_controller, delete_modbus_controller,
    test_modbus_controller, create_modbus_points_batch, get_modbus_points_by_controller,
    update_modbus_point, delete_modbus_point, read_modbus_controller_points_data,
    write_modbus_point_data,
    export_modbus_controller_config_file, import_modbus_configuration_from_file,
    validate_modbus_configuration_from_file
)
from .schema import (
    ModbusControllerCreateRequest, ModbusControllerUpdateRequest, ModbusControllerResponse,
    ModbusControllerListResponse, ModbusPointBatchCreateRequest, ModbusPointUpdateRequest,
    ModbusPointResponse, ModbusPointListResponse, ModbusPointBatchCreateResponse,
    ModbusControllerValuesResponse, ModbusPointWriteRequest, ModbusPointWriteResponse,
    ModbusConfigImportResponse, ModbusConfigValidationResponse,
    modbus_controller_response_example, modbus_controller_list_response_example,
    modbus_point_response_example, modbus_point_list_response_example,
    modbus_multi_point_data_response_example,
    modbus_point_write_response_example,
    PointType, ConfigFormat
)

router = APIRouter(tags=["modbus"])

@router.post(
    "/controllers",
    response_model=APIResponse[ModbusControllerResponse],
    response_model_exclude_unset=True,
    summary="Create Modbus controller (with connection test)",
    responses=parse_responses({
        200: ("Controller created successfully", ModbusControllerResponse, modbus_controller_response_example),
        400: ("Connection test failed", None)
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
    except ModbusConnectionException:
        raise HTTPException(status_code=400, detail="Connection test failed")
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
    summary="Update Modbus controller (with connection test)",
    responses=parse_responses({
        200: ("Controller updated successfully", ModbusControllerResponse),
        400: ("Connection test failed", None),
        404: ("Controller not found", None)
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
    except ModbusConnectionException:
        raise HTTPException(status_code=400, detail="Connection test failed")
    except Exception:
        raise HTTPException(status_code=500)

@router.delete(
    "/controllers/{controller_id}",
    response_model=APIResponse[None],
    response_model_exclude_unset=True,
    summary="Delete Modbus controller (clear related points)",
    responses=parse_responses({
        200: ("Controller deleted successfully", None),
        404: ("Controller not found", None)
    }, default=common_responses)
)
async def delete_controller(
    controller_id: str,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        success = await delete_modbus_controller(controller_id, db)
        if success:
            return APIResponse(code=200, message="Controller deleted successfully")
        else:
            raise HTTPException(status_code=404, detail="Controller not found")
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
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
    summary="Create multiple Modbus points for a controller",
    responses=parse_responses({
        200: ("Points created successfully", ModbusPointBatchCreateResponse),
        404: ("Controller not found", None)
    }, default=common_responses)
)
async def create_points_batch(
    payload: ModbusPointBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        result = await create_modbus_points_batch(payload, db)
        return APIResponse(code=200, message="Points created successfully", data=result)
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
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
        404: ("Point not found", None)
    }, default=common_responses)
)
async def update_point(
    point_id: str,
    payload: ModbusPointUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        result = await update_modbus_point(point_id, payload, db)
        return APIResponse(code=200, message="Point updated successfully", data=result)
    except ModbusPointNotFoundException:
        raise HTTPException(status_code=404, detail="Point not found")
    except ModbusValidationException:
        raise HTTPException(status_code=400, detail="No data to update")
    except Exception:
        raise HTTPException(status_code=500)

@router.delete(
    "/points/{point_id}",
    response_model=APIResponse[None],
    response_model_exclude_unset=True,
    summary="Delete a Modbus point",
    responses=parse_responses({
        200: ("Point deleted successfully", None),
        404: ("Point not found", None)
    }, default=common_responses)
)
async def delete_point(
    point_id: str,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        success = await delete_modbus_point(point_id, db)
        if success:
            return APIResponse(code=200, message="Point deleted successfully")
        else:
            raise HTTPException(status_code=404, detail="Point not found")
    except ModbusPointNotFoundException:
        raise HTTPException(status_code=404, detail="Point not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.get(
    "/controllers/{controller_id}/points/data",
    response_model=APIResponse[ModbusControllerValuesResponse],
    response_model_exclude_unset=True,
    summary="Read values from all points of a controller",
    responses=parse_responses({
        200: ("Controller values read successfully", ModbusControllerValuesResponse, modbus_multi_point_data_response_example),
        404: ("Controller not found", None),
        400: ("Controller not connected or read failed", None)
    }, default=common_responses)
)
async def read_controller_points_data(
    controller_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    modbus: Annotated[ModbusManager, Depends(get_modbus)],
    point_type: PointType = Query(None, description="Filter by point type (coil/input/holding_register/input_register)")
):
    try:
        result = await read_modbus_controller_points_data(controller_id, db, modbus, point_type=point_type)
        return APIResponse(code=200, message="Controller values read successfully", data=result)
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except ModbusValidationException:
        raise HTTPException(status_code=400, detail="Controller not connected or read failed")
    except ModbusReadException:
        raise HTTPException(status_code=400, detail="Controller not connected or read failed")
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
    except ModbusPointNotFoundException:
        raise HTTPException(status_code=404, detail="Point not found")
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except ModbusValidationException:
        raise HTTPException(status_code=409, detail="Point does not support writing or validation failed")
    except ModbusRangeValidationException:
        raise HTTPException(status_code=422, detail="Value is outside the valid range")
    except ModbusWriteException:
        raise HTTPException(status_code=400, detail="Write operation failed")
    except Exception:
        raise HTTPException(status_code=500)

@router.get(
    "/controllers/{controller_id}/export",
    summary="Export Modbus Controller Configuration",
    description="Export Modbus controller and its points configuration as downloadable file"
)
async def export_controller_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    controller_id: str,
    format: ConfigFormat = Query(ConfigFormat.native, description="Export format")
):
    """Export controller configuration as file"""
    try:
        result = await export_modbus_controller_config_file(controller_id, format, db)
        
        # Return file download
        return FileResponse(
            path=result["file_path"],
            filename=result["filename"],
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={result['filename']}"
            }
        )
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except ModbusConfigException:
        raise HTTPException(status_code=400, detail="Export failed")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/config/import",
    response_model=APIResponse[ModbusConfigImportResponse],
    response_model_exclude_unset=True,
    summary="Import Modbus Configuration",
    description="Import Modbus configuration from uploaded JSON file"
)
async def import_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(..., description="Configuration file (JSON format)"),
    format: ConfigFormat = Form(ConfigFormat.native, description="Import format")
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
        
        result = await import_modbus_configuration_from_file(config, format, db)
        return APIResponse(code=200, message="Configuration imported successfully", data=result)
    except ModbusConfigFormatMismatchException as e:
        raise HTTPException(status_code=422, detail=f"Format mismatch: {str(e)}")
    except ModbusConfigException as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500)

@router.post(
    "/config/validate",
    response_model=APIResponse[ModbusConfigValidationResponse],
    response_model_exclude_unset=True,
    summary="Validate Modbus Configuration",
    description="Validate Modbus configuration from uploaded file"
)
async def validate_config(
    file: UploadFile = File(..., description="Configuration file (JSON format)"),
    format: ConfigFormat = Form(ConfigFormat.native, description="Configuration format")
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
    except ModbusConfigFormatMismatchException as e:
        raise HTTPException(status_code=422, detail=f"Format mismatch: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500)