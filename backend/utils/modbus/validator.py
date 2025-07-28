import logging
from dataclasses import dataclass
from typing import Dict, Any, List
from .data_converter import ModbusPointType
from utils.custom_exception import ModbusConfigFormatException

logger = logging.getLogger(__name__)

@dataclass
class ModbusConfigValidationResult:
    """Configuration validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class ModbusConfigValidator:
    """Validate Modbus configuration formats"""
    
    @classmethod
    def validate_native_format(cls, config: Dict[str, Any]) -> ModbusConfigValidationResult:
        """Validate native format configuration"""
        errors = []
        warnings = []
        
        # Check for ThingsBoard format indicators
        if "master" in config and "slaves" in config.get("master", {}):
            raise ModbusConfigFormatException(
                "Configuration appears to be in ThingsBoard format, but native format was expected. "
                "Please select 'thingsboard' format for this file."
            )
        
        # Validate required sections
        if "controller" not in config or "points" not in config:
            raise ModbusConfigFormatException("Missing 'controller' and 'points' sections in native format")
        
        # Validate controller fields
        controller = config["controller"]
        required_fields = ["name", "host", "port"]
        for field in required_fields:
            if field not in controller:
                raise ModbusConfigFormatException(f"Missing required field '{field}' in controller")
        
        # Validate points
        for i, point in enumerate(config["points"]):
            required_fields = ["name", "type", "data_type", "address"]
            for field in required_fields:
                if field not in point:
                    raise ModbusConfigFormatException(f"Point {i}: Missing required field '{field}'")
            
            # Validate point type
            if "type" in point and point["type"] not in [t.value for t in ModbusPointType]:
                raise ModbusConfigFormatException(f"Point {i}: Invalid type '{point['type']}'")
        
        return ModbusConfigValidationResult(is_valid=True, errors=errors, warnings=warnings)
    
    @classmethod
    def validate_thingsboard_format(cls, config: Dict[str, Any]) -> ModbusConfigValidationResult:
        """Validate ThingsBoard format configuration"""
        errors = []
        warnings = []
        
        # Check for native format indicators
        if "controller" in config and "points" in config:
            raise ModbusConfigFormatException(
                "Configuration appears to be in native format, but ThingsBoard format was expected. "
                "Please select 'native' format for this file."
            )
        
        # Validate required sections
        if "master" not in config:
            raise ModbusConfigFormatException("Missing 'master' section in ThingsBoard format")
        
        master = config["master"]
        if "slaves" not in master:
            raise ModbusConfigFormatException("Missing 'slaves' section in master")
        
        slaves = master["slaves"]
        if len(slaves) == 0:
            raise ModbusConfigFormatException("No slaves found in ThingsBoard configuration")
        elif len(slaves) > 1:
            raise ModbusConfigFormatException("Only single controller import is supported. Multiple slaves found.")
        
        # Validate slave configuration
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
        
        return ModbusConfigValidationResult(is_valid=True, errors=errors, warnings=warnings)
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any], format: str) -> ModbusConfigValidationResult:
        """Validate configuration based on format"""
        if format == "native":
            return cls.validate_native_format(config)
        elif format == "thingsboard":
            return cls.validate_thingsboard_format(config)
        else:
            raise ModbusConfigFormatException(f"Unsupported format: {format}")