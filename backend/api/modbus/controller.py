import json
from typing import Annotated, Union
from core.dependencies import get_db
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from extensions.modbus import get_modbus, ModbusManager
from utils.response import APIResponse, parse_responses, common_responses
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from utils.custom_exception import (
    ModbusConnectionException, ModbusControllerNotFoundException,
    ModbusPointNotFoundException, ModbusReadException, ModbusValidationException,
    ModbusWriteException, ModbusRangeValidationException,
    ModbusConfigException, ModbusConfigFormatException,
    ModbusControllerDuplicateException, ModbusPointDuplicateException
)
from .services import (
    create_modbus_controller, get_modbus_controllers, update_modbus_controller, delete_modbus_controllers,
    test_modbus_controller, create_modbus_points_batch, get_modbus_points_by_controller,
    update_modbus_point, delete_modbus_points, read_modbus_controller_points_data,
    write_modbus_point_data,
    export_modbus_controller_config_data, import_modbus_configuration_from_file,
    export_modbus_controller_config_data
)
from .schema import (
    ModbusControllerCreateRequest, ModbusControllerUpdateRequest, ModbusControllerResponse,
    ModbusControllerListResponse, ModbusPointBatchCreateRequest, ModbusPointUpdateRequest,
    ModbusPointResponse, ModbusPointListResponse,
    ModbusControllerValuesResponse, ModbusPointWriteRequest, ModbusPointWriteResponse,
    modbus_controller_response_example, modbus_controller_list_response_example,
    modbus_point_response_example, modbus_point_list_response_example,
    modbus_multi_point_data_response_example,
    modbus_point_write_response_example,
    modbus_point_batch_create_failed_response_example,
    ModbusControllerDeleteRequest, ModbusPointDeleteRequest,
    ModbusControllerDeleteResponse, ModbusPointDeleteResponse,
    ModbusControllerDeleteFailedResponse, ModbusPointDeleteFailedResponse,
    modbus_controller_delete_response_example, modbus_point_delete_response_example,
    modbus_controller_delete_failed_response_example, modbus_point_delete_failed_response_example,
    modbus_point_batch_create_simple_response_example, modbus_point_batch_create_partial_response_example,
    modbus_config_import_simple_response_example, modbus_config_import_partial_response_example,
    modbus_config_import_failed_response_example,
    PointType, ConfigFormat, ImportMode,
    ModbusPointBatchCreateResponse, ModbusConfigImportResponse, 
    create_modbus_point_batch_response, create_modbus_config_import_response
)

router = APIRouter(tags=["modbus"])

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
    status: bool = Query(None, description="過濾控制器狀態 (true=連線, false=未連線)"),
    name: str = Query(None, description="過濾控制器名稱")
):
    try:
        data = await get_modbus_controllers(db, status=status, name=name)
        return APIResponse(code=200, message="Get controller list successfully", data=data)
    except Exception:
        raise HTTPException(status_code=500)
    
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
    request: ModbusControllerDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
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
    point_type: PointType = Query(None, description="過濾點位類型 (coil/input/holding_register/input_register)")
):
    try:
        data = await get_modbus_points_by_controller(controller_id, db, point_type=point_type)
        return APIResponse(code=200, message="Get point list successfully", data=data)
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/points",
    response_model=APIResponse[ModbusPointBatchCreateResponse],
    response_model_exclude_unset=True,
    summary="Create multiple Modbus points for a controller",
    responses=parse_responses({
        200: ("All points created successfully", ModbusPointBatchCreateResponse, modbus_point_batch_create_simple_response_example),
        207: ("Points created with partial success", ModbusPointBatchCreateResponse, modbus_point_batch_create_partial_response_example),
        400: ("All points failed to create", ModbusPointBatchCreateResponse, modbus_point_batch_create_failed_response_example),
        404: ("Controller not found", None)
    }, default=common_responses)
)
async def create_points_batch(
    request: ModbusPointBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Create multiple Modbus points for a controller"""
    try:
        result = await create_modbus_points_batch(request, db)
        
        if result.success_count > 0 and result.skipped_count == 0 and result.failed_count == 0:
            status_code = 200
            message = "All points created successfully"
            response_data = create_modbus_point_batch_response(result)
        elif result.success_count == 0:
            status_code = 400
            message = "All points failed to create"
            response_data = {
                "results": result.results,
                "total_requested": result.total_requested,
                "skipped_count": result.skipped_count,
                "failed_count": result.failed_count
            }
        else:
            status_code = 207
            message = "Points created with partial success"
            response_data = {
                "results": result.results,
                "total_requested": result.total_requested,
                "success_count": result.success_count,
                "skipped_count": result.skipped_count,
                "failed_count": result.failed_count
            }
        
        api_response = APIResponse(code=status_code, message=message, data=response_data)
        
        if status_code != 200:
            raise HTTPException(status_code=status_code, detail=api_response.dict(exclude_none=True))
        
        return api_response
        
    except HTTPException:
        raise
    except ModbusControllerNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
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
    request: ModbusPointDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
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
    point_type: PointType = Query(None, description="過濾點位類型 (coil/input/holding_register/input_register)"),
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
        raise HTTPException(status_code=500, detail="Write operation failed")
    except ModbusPointNotFoundException:
        raise HTTPException(status_code=404, detail="Point not found")
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except ModbusValidationException as e:
        if "does not support writing" in str(e):
            raise HTTPException(status_code=409, detail="Point does not support writing or validation failed")
        else:
            raise HTTPException(status_code=400, detail="Point does not support writing or validation failed")
    except ModbusRangeValidationException:
        raise HTTPException(status_code=422, detail="Value is outside the valid range")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/import/controller",
    response_model=APIResponse[ModbusConfigImportResponse],
    response_model_exclude_unset=True,
    summary="Import Modbus Controller Configuration",
    responses=parse_responses({
        200: ("Controller imported successfully", ModbusConfigImportResponse, modbus_config_import_simple_response_example),
        207: ("Controller imported with partial success", ModbusConfigImportResponse, modbus_config_import_partial_response_example),
        400: ("Controller failed to import / All points failed to imports", ModbusConfigImportResponse, modbus_config_import_failed_response_example),
        409: ("Controller already exists / All points already exists", ModbusConfigImportResponse, modbus_config_import_simple_response_example),
        415: ("Unsupported configuration format", None)
    }, default=common_responses)
)
async def import_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(..., description="Modbus 配置文件 (JSON 格式)"),
    config_format: ConfigFormat = Form(ConfigFormat.native, description="配置文件格式 (native: 原生格式, thingsboard: ThingsBoard 格式)"),
    duplicate_handling: ImportMode = Form(ImportMode.SKIP_CONTROLLER, description="重複項目處理方式 (skip_controller: 跳過整個控制器, overwrite_controller: 覆蓋整個控制器, skip_duplicates_point: 跳過重複點位, overwrite_duplicates_point: 覆蓋重複點位)")
):
    """
    Import Modbus controller configuration from JSON file
    """
    try:
        if not file.filename.endswith('.json'):
            raise ModbusConfigFormatException("Unsupported configuration format")
        
        content = await file.read()
        try:
            config = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError:
            raise ModbusConfigFormatException("Invalid JSON format")
        
        result = await import_modbus_configuration_from_file(config, config_format, db, duplicate_handling)
        
        if result.success_count > 0 and result.skipped_count == 0 and result.failed_count == 0:
            status_code = 200
            message = "Controller imported successfully"
            response_data = create_modbus_config_import_response(result)
        elif result.success_count == 0:
            status_code = 400
            message = "All points failed to import"
            response_data = {
                "controller_id": result.controller_id,
                "controller_name": result.controller_name,
                "points": result.points,
                "total_points": result.total_points,
                "skipped_count": result.skipped_count,
                "failed_count": result.failed_count
            }
        else:
            status_code = 207
            message = "Controller imported with partial success"
            response_data = {
                "controller_id": result.controller_id,
                "controller_name": result.controller_name,
                "points": result.points,
                "total_points": result.total_points,
                "success_count": result.success_count,
                "skipped_count": result.skipped_count,
                "failed_count": result.failed_count
            }
        
        api_response = APIResponse(code=status_code, message=message, data=response_data)
        
        if status_code != 200:
            raise HTTPException(status_code=status_code, detail=api_response.dict(exclude_none=True))        
        return api_response
        
    except HTTPException:
        raise
    except ModbusConfigFormatException:
        raise HTTPException(status_code=415, detail="Unsupported configuration format")
    except ModbusConfigException:
        raise HTTPException(status_code=400, detail="Controller failed to import")
    except Exception:
        raise HTTPException(status_code=500)

@router.post(
    "/export/{controller_id}",
    summary="Export Modbus Controller Configuration",
    responses=parse_responses({
        200: ("Configuration exported successfully", None),
        404: ("Controller not found", None)
    }, default=common_responses)
)
async def export_controller_config(
    controller_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    export_format: ConfigFormat = Form(ConfigFormat.native, description="匯出格式 (native: 原生格式, thingsboard: ThingsBoard 格式)")
):
    """
    Export Modbus controller configuration to JSON file (no server file storage)
    """
    try:
        result = await export_modbus_controller_config_data(controller_id, export_format, db)
        
        # Convert config to JSON string
        json_content = json.dumps(result["config_data"], indent=2, ensure_ascii=False)
        
        # Create streaming response
        return StreamingResponse(
            iter([json_content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={result['filename']}"
            }
        )
        
    except ModbusControllerNotFoundException:
        raise HTTPException(status_code=404, detail="Controller not found")
    except Exception:
        raise HTTPException(status_code=500)