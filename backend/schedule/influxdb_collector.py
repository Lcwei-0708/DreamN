import logging
from datetime import datetime
from core.config import settings
from typing import List, Dict, Any
from sqlalchemy import select, func
from core.dependencies import get_db
from core.database import get_influxdb
from extensions.modbus import get_modbus
from models.modbus_point import ModbusPoint
from models.modbus_controller import ModbusController

logger = logging.getLogger("influxdb_collector")

class InfluxDBCollector:    
    def __init__(self):
        self.modbus_manager = get_modbus()
    
    async def collect_and_write_data(self):
        """Collect and write data to InfluxDB"""
        try:
            logger.info("Starting to collect and write data to InfluxDB...")
            async for db in get_db():
                # Query all connected controllers
                result = await db.execute(
                    select(ModbusController).where(ModbusController.status == True)
                )
                active_controllers = result.scalars().all()
                
                if not active_controllers:
                    logger.info("No connected controllers found")
                    return
                
                logger.info(f"Found {len(active_controllers)} connected controllers")
                
                total_points_collected = 0
                total_points_failed = 0
                
                for controller in active_controllers:
                    try:
                        points_collected, points_failed = await self._collect_controller_data(
                            controller, db
                        )
                        total_points_collected += points_collected
                        total_points_failed += points_failed
                        
                    except Exception as e:
                        logger.error(f"Error collecting data for controller {controller.name}: {e}")
                        total_points_failed += 1
                
                logger.info(f"Data collection completed - Success: {total_points_collected}, Failed: {total_points_failed}")
                break
                
        except Exception as e:
            logger.error(f"Error collecting Modbus data: {e}")
    
    async def _collect_controller_data(self, controller, db) -> tuple[int, int]:
        """Collect all points data for a single controller"""
        try:            
            # Query all points for the controller
            points_result = await db.execute(
                select(ModbusPoint).where(ModbusPoint.controller_id == controller.id)
            )
            points = points_result.scalars().all()
            
            if not points:
                logger.debug(f"Controller {controller.name} has no points configured")
                return 0, 0
            
            logger.debug(f"Starting to collect data for {len(points)} points of controller {controller.name}")
            
            # Prepare InfluxDB points
            influx_points = []
            points_collected = 0
            points_failed = 0
            
            for point in points:
                try:
                    # Read point data
                    data_result = await self.modbus_manager.read_point_data(
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
                    
                    # Create InfluxDB point
                    influx_point = self._create_influx_point(
                        controller, point, data_result
                    )
                    influx_points.append(influx_point)
                    points_collected += 1
                    
                except Exception as e:
                    logger.error(f"Failed to read point {point.name}: {e}")
                    points_failed += 1
                    
                    # Even if reading fails, record error status to InfluxDB
                    error_point = self._create_error_influx_point(
                        controller, point, str(e)
                    )
                    influx_points.append(error_point)
            
            # Batch write to InfluxDB
            if influx_points:
                await self._write_to_influxdb(influx_points)
                logger.debug(f"Controller {controller.name} successfully wrote {len(influx_points)} points to InfluxDB")
            
            return points_collected, points_failed
            
        except Exception as e:
            logger.error(f"Error collecting data for controller {controller.name}: {e}")
            return 0, 1
    
    def _create_influx_point(self, controller, point, data_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create InfluxDB point"""
        return {
            "measurement": "modbus_data",
            "tags": {
                "controller_id": controller.id,
                "controller_name": controller.name,
                "point_id": point.id,
                "point_name": point.name,
                "point_type": point.type,
                "data_type": point.data_type,
                "unit": point.unit or "",
                "unit_id": str(point.unit_id)
            },
            "fields": {
                "value": data_result.get("final_value"),
                "raw_value": data_result.get("raw_value"),
                "status": "ok"
            },
            "time": datetime.utcnow()
        }
    
    def _create_error_influx_point(self, controller, point, error_message: str) -> Dict[str, Any]:
        """Create InfluxDB point with error status"""
        return {
            "measurement": "modbus_data",
            "tags": {
                "controller_id": controller.id,
                "controller_name": controller.name,
                "point_id": point.id,
                "point_name": point.name,
                "point_type": point.type,
                "data_type": point.data_type,
                "unit": point.unit or "",
                "unit_id": str(point.unit_id)
            },
            "fields": {
                "value": None,
                "raw_value": None,
                "status": "error",
                "error_message": error_message
            },
            "time": datetime.utcnow()
        }
    
    async def _write_to_influxdb(self, points: List[Dict[str, Any]]):
        """Write points to InfluxDB"""
        try:
            influxdb = get_influxdb()
            write_api = influxdb["write_api"]
            
            # Convert to InfluxDB format
            influx_records = []
            for point in points:
                record = {
                    "measurement": point["measurement"],
                    "tags": point["tags"],
                    "fields": point["fields"],
                    "time": point["time"]
                }
                influx_records.append(record)
            
            # Write to InfluxDB
            write_api.write(
                bucket=settings.INFLUXDB_BUCKET,
                record=influx_records
            )
            
            logger.debug(f"Successfully wrote {len(influx_records)} points to InfluxDB")
            
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")
            raise