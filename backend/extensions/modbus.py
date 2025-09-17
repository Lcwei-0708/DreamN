import struct
import logging
import asyncio
from datetime import datetime
from pymodbus.client import ModbusTcpClient
from typing import Dict, Optional, Any, List, Union

logger = logging.getLogger("modbus")

class ModbusManager:
    def __init__(self):
        self.clients: Dict[str, ModbusTcpClient] = {}
        self.client_status: Dict[str, bool] = {}
        self._initialized = False
        self.controller_mapping: Dict[str, str] = {}

    async def _update_controller_status(self, controller_id: str, status: bool):
        """Update controller status in database"""
        try:
            from sqlalchemy import update
            from core.dependencies import get_db
            from models.modbus_controller import ModbusController
            
            async for db in get_db():
                await db.execute(
                    update(ModbusController)
                    .where(ModbusController.id == controller_id)
                    .values(status=status)
                )
                await db.commit()
                break
        except Exception as e:
            logger.error(f"Failed to update controller status {controller_id}: {e}")

    async def connect(self, client_id: str) -> bool:
        """Connect to Modbus device"""
        client = self.clients.get(client_id)
        if not client:
            logger.error(f"Client not found: {client_id}")
            return False
        
        try:
            # Check if already connected
            if hasattr(client, "connected") and client.connected:
                logger.info(f"[{client_id}] Already connected")
                self.client_status[client_id] = True
                return True
            
            # Attempt to connect
            connected = await asyncio.get_event_loop().run_in_executor(
                None, client.connect
            )
            self.client_status[client_id] = connected
            
            if connected:
                logger.info(f"[{client_id}] Connection successful")
            else:
                logger.warning(f"[{client_id}] Connection failed")
            return connected
        except Exception as e:
            logger.exception(f"[{client_id}] Connection error: {e}")
            self.client_status[client_id] = False
            return False

    def disconnect(self, client_id: str):
        """Disconnect from Modbus device"""
        client = self.clients.get(client_id)
        if client:
            try:
                client.close()
                self.client_status[client_id] = False
                logger.info(f"[{client_id}] Connection closed")
            except Exception as e:
                logger.error(f"[{client_id}] Close failed: {e}")

    async def is_healthy(self, client_id: str) -> bool:
        """Check if client connection is healthy"""
        client = self.clients.get(client_id)
        if not client:
            return False
        
        try:
            # First check if we have a stored status
            if client_id in self.client_status and self.client_status[client_id]:
                # Try to verify the connection is still alive
                if hasattr(client, "is_socket_open"):
                    is_open = await asyncio.get_event_loop().run_in_executor(
                        None, client.is_socket_open
                    )
                    if is_open:
                        return True
            
            # If we reach here, connection is not healthy
            self.client_status[client_id] = False
            return False
            
        except Exception as e:
            logger.error(f"[{client_id}] Health check failed: {e}")
            self.client_status[client_id] = False
            return False

    async def read_modbus_data(self, client_id: str, point_type: str, address: int, count: int, unit_id: int) -> Any:
        """Read data from Modbus device based on point type"""
        from utils.custom_exception import ModbusReadException
        
        client = self.clients.get(client_id)
        if not client:
            raise ModbusReadException(f"Client {client_id} not found")
        
        try:
            result = None
            
            if point_type == "coil":
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: client.read_coils(address, count=count, device_id=unit_id)
                )
            elif point_type == "input":
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: client.read_discrete_inputs(address, count=count, device_id=unit_id)
                )
            elif point_type == "holding_register":
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: client.read_holding_registers(address, count=count, device_id=unit_id)
                )
            elif point_type == "input_register":
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: client.read_input_registers(address, count=count, device_id=unit_id)
                )
            else:
                raise ModbusReadException(f"Unsupported point type: {point_type}")
            
            if result.isError():
                raise ModbusReadException(f"Modbus read error: {result}")
            
            if point_type in ["coil", "input"]:
                return result.bits[:count]
            else:
                return result.registers[:count]
                
        except ModbusReadException:
            raise
        except Exception as e:
            logger.error(f"[{client_id}] Read data failed: {e}")
            raise ModbusReadException(f"Failed to read data: {str(e)}")

    async def write_modbus_data(self, client_id: str, point_type: str, address: int, value: Union[bool, int, float], unit_id: int) -> List[Union[bool, int]]:
        """Write data to Modbus device based on point type"""
        from utils.custom_exception import ModbusWriteException
        
        client = self.clients.get(client_id)
        if not client:
            raise ModbusWriteException(f"Client {client_id} not found")
        
        try:
            result = None
            
            if point_type == "coil":
                # Write single coil (boolean value)
                if not isinstance(value, bool):
                    raise ModbusWriteException(f"Coil requires boolean value, got {type(value)}")
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: client.write_coil(address, value, device_id=unit_id)
                )
                return [value]
                
            elif point_type == "holding_register":
                # Write single holding register (integer value)
                if not isinstance(value, (int, float)):
                    raise ModbusWriteException(f"Holding register requires numeric value, got {type(value)}")
                
                # Convert float to int if needed
                int_value = int(value)
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: client.write_register(address, int_value, device_id=unit_id)
                )
                return [int_value]
                
            else:
                raise ModbusWriteException(f"Unsupported point type for writing: {point_type}")
            
            if result.isError():
                raise ModbusWriteException(f"Modbus write error: {result}")
            
            return [value] if point_type == "coil" else [int(value)]
                
        except ModbusWriteException:
            raise
        except Exception as e:
            logger.error(f"[{client_id}] Write data failed: {e}")
            raise ModbusWriteException(f"Failed to write data: {str(e)}")

    async def write_point_data(self, host: str, port: int, point_type: str, address: int, 
                        value: Union[bool, int, float], unit_id: int, data_type: str, 
                        formula: Optional[str] = None, min_value: Optional[float] = None, 
                        max_value: Optional[float] = None) -> Dict[str, Any]:
        """Write data to a specific Modbus point with validation"""
        from utils.custom_exception import ModbusWriteException, ModbusRangeValidationException
        
        client_id = f"tcp_{host}_{port}"
        
        try:
            if client_id not in self.clients:
                logger.warning(f"[{client_id}] Client not found, creating new connection...")
                self.create_tcp(host, port, 30)  # Use default timeout
            
            # Check if connection is healthy, if not try to reconnect
            if not await self.is_healthy(client_id):
                logger.warning(f"[{client_id}] Connection not healthy, attempting to reconnect...")
                success = await self.connect(client_id)
                if not success:
                    raise ModbusWriteException("Failed to reconnect to Modbus device")
                logger.info(f"[{client_id}] Reconnection successful")
            else:
                logger.debug(f"[{client_id}] Connection is healthy")
            
            # Validate range if min_value and max_value are provided
            if min_value is not None and max_value is not None and isinstance(value, (int, float)):
                if value < min_value or value > max_value:
                    raise ModbusRangeValidationException(f"Value {value} is outside the valid range [{min_value}, {max_value}]")
            
            # Apply reverse formula if provided (for holding registers)
            write_value = value
            if formula and point_type == "holding_register" and isinstance(value, (int, float)):
                try:
                    # Simple reverse formula: if formula is "x * 0.1", reverse is "x / 0.1"
                    if "*" in formula:
                        parts = formula.split("*")
                        if len(parts) == 2:
                            multiplier = float(parts[1].strip())
                            write_value = value / multiplier
                    elif "/" in formula:
                        parts = formula.split("/")
                        if len(parts) == 2:
                            divisor = float(parts[1].strip())
                            write_value = value * divisor
                    else:
                        # For more complex formulas, just use the original value
                        write_value = value
                except Exception as e:
                    logger.warning(f"Failed to apply reverse formula: {e}, using original value")
                    write_value = value
            
            raw_data = await self.write_modbus_data(client_id, point_type, address, write_value, unit_id)
            
            return {
                "write_value": value,
                "raw_data": raw_data,
                "write_time": datetime.now().isoformat(),
                "success": True
            }
            
        except (ModbusWriteException, ModbusRangeValidationException):
            raise
        except Exception as e:
            logger.error(f"Failed to write point data to {client_id}: {e}")
            raise ModbusWriteException(f"Failed to write point data: {str(e)}")

    def _convert_raw_data(self, raw_data: List[Union[bool, int]], data_type: str, length: int) -> Union[bool, int, float, List]:
        """Convert raw Modbus data to specified data type"""
        try:
            if length == 1:
                # Single value conversion
                value = raw_data[0]
                
                # Boolean types
                if data_type.lower() in ["bool", "boolean"]:
                    return bool(value)
                    
                # Signed integer types
                elif data_type.lower() in ["int8"]:
                    # Convert to signed 8-bit
                    return int(value) if value < 128 else int(value) - 256
                elif data_type.lower() in ["int16", "short"]:
                    # Convert to signed 16-bit
                    return int(value) if value < 32768 else int(value) - 65536
                elif data_type.lower() in ["int32", "int", "long"]:
                    return int(value)
                    
                # Unsigned integer types
                elif data_type.lower() in ["uint8", "byte"]:
                    return int(value) & 0xFF
                elif data_type.lower() in ["uint16", "ushort", "word"]:
                    return int(value) & 0xFFFF
                elif data_type.lower() in ["uint32", "uint", "ulong", "dword"]:
                    return int(value) & 0xFFFFFFFF
                    
                # Float types
                elif data_type.lower() in ["float", "float32", "real"]:
                    return float(value)
                elif data_type.lower() in ["double", "float64"]:
                    return float(value)
                    
                # Default fallback
                else:
                    logger.warning(f"Unknown data type: {data_type}, using raw value")
                    return value
                    
            elif length == 2:
                # Two-register conversions
                if len(raw_data) < 2:
                    logger.warning(f"Expected 2 registers but got {len(raw_data)}")
                    return raw_data[0] if raw_data else 0
                
                reg1, reg2 = raw_data[0], raw_data[1]
                
                # Signed 32-bit integer
                if data_type.lower() in ["int32", "int", "long"]:
                    combined = (reg1 << 16) | reg2
                    return combined if combined < 2147483648 else combined - 4294967296
                    
                # Unsigned 32-bit integer  
                elif data_type.lower() in ["uint32", "uint", "ulong", "dword"]:
                    return (reg1 << 16) | reg2
                    
                # 32-bit float
                elif data_type.lower() in ["float", "float32", "real"]:
                    try:
                        # IEEE 754 float format (big-endian)
                        combined = (reg1 << 16) | reg2
                        return struct.unpack('>f', struct.pack('>I', combined))[0]
                    except:
                        # Fallback: treat as scaled integer
                        return float((reg1 << 16) | reg2)
                
                # For other types with length 2, try to combine as unsigned by default
                else:
                    logger.info(f"Data type {data_type} with length 2, combining as unsigned integer")
                    return (reg1 << 16) | reg2
                    
            elif length == 4:
                # Four-register conversions (mainly for double)
                if len(raw_data) < 4:
                    logger.warning(f"Expected 4 registers but got {len(raw_data)}")
                    return raw_data[0] if raw_data else 0
                
                if data_type.lower() in ["double", "float64"]:
                    try:
                        # IEEE 754 double format (big-endian)
                        combined = (raw_data[0] << 48) | (raw_data[1] << 32) | (raw_data[2] << 16) | raw_data[3]
                        return struct.unpack('>d', struct.pack('>Q', combined))[0]
                    except:
                        # Fallback
                        return float(raw_data[0])
                else:
                    # Return as list for other 4-register types
                    return raw_data
                    
            else:
                # Multiple registers (length > 4 or other cases)
                if data_type.lower() in ["int16", "short"]:
                    # Convert each register to signed 16-bit
                    return [int(val) if val < 32768 else int(val) - 65536 for val in raw_data]
                elif data_type.lower() in ["uint16", "ushort", "word"]:
                    # Keep as unsigned 16-bit
                    return [int(val) & 0xFFFF for val in raw_data]
                else:
                    # Return raw data for unknown types
                    return raw_data
                    
        except Exception as e:
            logger.error(f"Data conversion failed for type {data_type}: {e}")
            return raw_data[0] if length == 1 else raw_data

    def _apply_formula(self, value: Union[int, float], formula: Optional[str]) -> Union[int, float]:
        """Apply conversion formula to the value"""
        if not formula or formula.strip() == "" or formula.strip().lower() == "null":
            return value
            
        try:
            # Replace 'x' with the actual value
            formula_str = formula.replace('x', str(value))
            
            # Evaluate the formula safely (basic math operations only)
            allowed_operators = ['+', '-', '*', '/', '(', ')', '.', ' ']
            allowed_functions = ['abs', 'round', 'int', 'float']
            
            # Basic security check
            if any(char.isalpha() and char not in 'x' for char in formula if char not in ''.join(allowed_functions)):
                # If there are alphabetic characters other than 'x' and allowed functions, it might be unsafe
                safe_chars = set('0123456789+-*/().,x ')
                safe_chars.update(''.join(allowed_functions))
                if not all(c in safe_chars for c in formula.lower()):
                    logger.warning(f"Potentially unsafe formula detected: {formula}")
                    return value
            
            # Replace function names for evaluation
            eval_formula = formula_str
            for func in allowed_functions:
                eval_formula = eval_formula.replace(func, func)
            
            result = eval(eval_formula)
            return float(result) if '.' in str(result) else int(result)
            
        except Exception as e:
            logger.error(f"Formula evaluation failed for '{formula}' with value {value}: {e}")
            return value

    async def read_point_data(self, host: str, port: int, point_type: str, address: int, 
                       length: int, unit_id: int, data_type: str, formula: Optional[str] = None, 
                       min_value: Optional[float] = None, max_value: Optional[float] = None) -> Dict[str, Any]:
        """Read data from a specific Modbus point and apply conversions"""
        from utils.custom_exception import ModbusReadException
        
        client_id = f"tcp_{host}_{port}"
        
        try:
            if client_id not in self.clients:
                logger.warning(f"[{client_id}] Client not found, creating new connection...")
                self.create_tcp(host, port, 30)  # Use default timeout
            
            # Check if connection is healthy, if not try to reconnect
            if not await self.is_healthy(client_id):
                logger.warning(f"[{client_id}] Connection not healthy, attempting to reconnect...")
                success = await self.connect(client_id)
                if not success:
                    raise ModbusReadException("Failed to reconnect to Modbus device")
                logger.info(f"[{client_id}] Reconnection successful")
            else:
                logger.debug(f"[{client_id}] Connection is healthy")
            
            raw_data = await self.read_modbus_data(client_id, point_type, address, length, unit_id)            
            converted_value = self._convert_raw_data(raw_data, data_type, length)
            
            final_value = converted_value
            if formula and isinstance(converted_value, (int, float)):
                final_value = self._apply_formula(converted_value, formula)
            
            # Validate range if min_value and max_value are provided
            range_valid = True
            range_message = None
            if min_value is not None and max_value is not None and isinstance(final_value, (int, float)):
                if final_value < min_value or final_value > max_value:
                    range_valid = False
                    range_message = f"Value {final_value} is outside the valid range [{min_value}, {max_value}]"
                    logger.warning(f"[{client_id}] Range validation failed: {range_message}")
            
            return {
                "raw_data": raw_data,
                "converted_value": converted_value,
                "final_value": final_value,
                "data_type": data_type,
                "read_time": datetime.now().isoformat(),
                "range_valid": range_valid,
                "range_message": range_message,
                "min_value": min_value,
                "max_value": max_value
            }
            
        except ModbusReadException:
            raise
        except Exception as e:
            logger.error(f"Failed to read point data from {client_id}: {e}")
            raise ModbusReadException(f"Failed to read point data: {str(e)}")

    def ensure_controller_client(self, controller_id: str, host: str, port: int, timeout: int = None) -> str:
        """Ensure controller client exists and return client_id"""
        client_id = f"tcp_{host}_{port}"
        
        if client_id not in self.clients:
            self.create_tcp(host, port, timeout)
            self.controller_mapping[client_id] = controller_id
        
        return client_id

    async def initialize_from_database(self):
        """Startup phase: Initialize all controller connections from database"""
        if self._initialized:
            return
            
        try:
            from sqlalchemy import select
            from core.dependencies import get_db
            from models.modbus_controller import ModbusController
            
            logger.info("Initializing Modbus connections from database...")
            
            try:
                async for db in get_db():
                    result = await db.execute(select(ModbusController))
                    controllers = result.scalars().all()
                    
                    logger.info(f"Found {len(controllers)} controller configurations")
                    
                    for ctrl in controllers:
                        try:
                            client_id = self.create_tcp(
                                host=ctrl.host,
                                port=ctrl.port, 
                                timeout=ctrl.timeout
                            )
                            
                            self.controller_mapping[client_id] = ctrl.id                            
                            success = await self.connect(client_id)                            
                            await self._update_controller_status(ctrl.id, success)
                            
                            if success:
                                logger.info(f"Controller {ctrl.name} ({ctrl.host}:{ctrl.port}) connected successfully")
                            else:
                                logger.warning(f"Controller {ctrl.name} ({ctrl.host}:{ctrl.port}) connection failed")
                                
                        except Exception as e:
                            logger.error(f"Error initializing controller {ctrl.name}: {e}")
                            if 'client_id' in locals():
                                self.controller_mapping[client_id] = ctrl.id
                            await self._update_controller_status(ctrl.id, False)
                    
                    await db.commit()
                    break
                    
                logger.info("Initialization complete")
                self._initialized = True
                
            except Exception as db_error:
                logger.warning(f"Database not ready, will retry later: {db_error}")
                
        except Exception as e:
            logger.error(f"Failed to initialize from database: {e}")

    def create_tcp(self, host: str, port: int, timeout: int = 30) -> str:
        timeout = timeout
        client_id = f"tcp_{host}_{port}"
        
        if client_id in self.clients:
            return client_id
            
        client = ModbusTcpClient(host=host, port=port, timeout=timeout)
        self.clients[client_id] = client
        self.client_status[client_id] = False
        logger.info(f"Created TCP client: {client_id}")
        return client_id

    def get_connection_status(self) -> Dict:
        """Get connection status summary"""
        try:
            return {
                "total_connections": len(self.clients),
                "initialized": self._initialized,
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting connection status: {e}")
            return {
                "total_connections": len(self.clients),
                "initialized": self._initialized,
                "last_check": datetime.now().isoformat(),
                "error": str(e)
            }

_modbus_instance: Optional[ModbusManager] = None

def get_modbus() -> ModbusManager:
    global _modbus_instance
    if _modbus_instance is None:
        _modbus_instance = ModbusManager()
    return _modbus_instance

def add_modbus(app):
    app.state.modbus = get_modbus()