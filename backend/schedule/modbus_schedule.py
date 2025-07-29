# Simplified Modbus schedule wrapper
import logging
from extensions.modbus import get_modbus

logger = logging.getLogger("modbus_schedule")

class ModbusSchedule:
    def __init__(self):
        self.modbus_manager = get_modbus()

    async def retry_failed_connections(self):
        """Scheduled task: retry failed controller connections"""
        try:
            from core.dependencies import get_db
            from models.modbus_controller import ModbusController
            from sqlalchemy import select
            
            logger.debug("Starting reconnect for controllers with status=false...")
            
            async for db in get_db():
                # Query database for controllers with status=false
                result = await db.execute(
                    select(ModbusController).where(ModbusController.status == False)
                )
                failed_controllers = result.scalars().all()
                
                if not failed_controllers:
                    logger.debug("No failed controllers found in database")
                    return
                
                logger.info(f"Found {len(failed_controllers)} failed controllers to retry")
                
                for ctrl in failed_controllers:
                    try:
                        # Ensure client exists
                        client_id = self.modbus_manager.ensure_controller_client(
                            ctrl.id, ctrl.host, ctrl.port, ctrl.timeout
                        )
                        
                        # Attempt connection
                        success = await self.modbus_manager.connect(client_id)
                        
                        # Update database status
                        await self.modbus_manager._update_controller_status(ctrl.id, success)
                        
                        if success:
                            logger.info(f"Reconnection successful: {ctrl.name} ({ctrl.host}:{ctrl.port})")
                        else:
                            logger.debug(f"Reconnection failed, will continue trying: {ctrl.name} ({ctrl.host}:{ctrl.port})")
                            
                    except Exception as e:
                        logger.error(f"Error during reconnection of {ctrl.name}: {e}")
                        await self.modbus_manager._update_controller_status(ctrl.id, False)
                
                await db.commit()
                break
                
        except Exception as e:
            logger.error(f"Error in scheduled retry failed connections: {e}")

    async def health_check_connections(self):
        """Scheduled task: health check active controllers"""
        try:
            from core.dependencies import get_db
            from models.modbus_controller import ModbusController
            from sqlalchemy import select
            
            logger.debug("Starting health check for controllers with status=true...")
            
            async for db in get_db():
                # Query database for controllers with status=true
                result = await db.execute(
                    select(ModbusController).where(ModbusController.status == True)
                )
                active_controllers = result.scalars().all()
                
                if not active_controllers:
                    logger.debug("No active controllers found in database")
                    return
                
                logger.debug(f"Found {len(active_controllers)} active controllers to health check")
                
                for ctrl in active_controllers:
                    try:
                        # Ensure client exists
                        client_id = self.modbus_manager.ensure_controller_client(
                            ctrl.id, ctrl.host, ctrl.port, ctrl.timeout
                        )
                        
                        # Check health status
                        is_healthy = await self.modbus_manager.is_healthy(client_id)
                        
                        if not is_healthy:
                            logger.warning(f"Health check failed for {ctrl.name} ({ctrl.host}:{ctrl.port}), attempting reconnection")
                            
                            # Attempt reconnection
                            success = await self.modbus_manager.connect(client_id)
                            
                            # Update database status
                            await self.modbus_manager._update_controller_status(ctrl.id, success)
                            
                            if success:
                                logger.info(f"Reconnection successful: {ctrl.name} ({ctrl.host}:{ctrl.port})")
                            else:
                                logger.warning(f"Reconnection failed: {ctrl.name} ({ctrl.host}:{ctrl.port})")
                        else:
                            logger.debug(f"Health check passed: {ctrl.name} ({ctrl.host}:{ctrl.port})")
                            
                    except Exception as e:
                        logger.error(f"Error during health check of {ctrl.name}: {e}")
                        await self.modbus_manager._update_controller_status(ctrl.id, False)
                
                await db.commit()
                break
                
        except Exception as e:
            logger.error(f"Error in scheduled health check: {e}")

    async def get_connection_status(self) -> dict:
        """API interface: get connection status summary"""
        try:
            return self.modbus_manager.get_connection_status()
        except Exception as e:
            logger.error(f"Error getting connection status: {e}")
            return {"error": str(e)}

    async def manual_reconnect_all(self):
        """API interface: manually trigger reconnection of all failed connections"""
        try:
            await self.retry_failed_connections()
            logger.info("Manual reconnect all triggered")
        except Exception as e:
            logger.error(f"Error in manual reconnect all: {e}")
            raise

    async def manual_health_check(self):
        """API interface: manually trigger health check"""
        try:
            await self.health_check_connections()
            logger.info("Manual health check triggered")
        except Exception as e:
            logger.error(f"Error in manual health check: {e}")
            raise
