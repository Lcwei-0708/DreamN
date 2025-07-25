import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class BaseServiceException(Exception):
    status_code: int = 500
    log_level: str = "error"

    def __init__(
        self, 
        message: str, 
        error_code: str = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = None,
        log_level: str = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        if log_level is not None:
            self.log_level = log_level
        
        log_msg = f"[{self.error_code}] | {self.message}"

        if self.log_level == "error":
            logger.error(log_msg)
        elif self.log_level == "warning":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        super().__init__(self.message)

class ServerException(BaseServiceException):
    """Server exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Server error"
        super().__init__(message, "SERVER_ERROR", details, status_code=500, log_level="error")

class UserNotFoundException(BaseServiceException):
    """User not found exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "User not found"
        super().__init__(message, "USER_NOT_FOUND", details, status_code=404, log_level="warning")

class EmailAlreadyExistsException(BaseServiceException):
    """Email already exists exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Email already exists"
        super().__init__(message, "EMAIL_ALREADY_EXISTS", details, status_code=409, log_level="warning")

class InvalidPasswordException(BaseServiceException):
    """Invalid password exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Invalid password"
        super().__init__(message, "INVALID_PASSWORD", details, status_code=401, log_level="warning")

class RoleNotFoundException(BaseServiceException):
    """Role not found exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Role not found"
        super().__init__(message, "ROLE_NOT_FOUND", details, status_code=404, log_level="warning")

class RoleAlreadyExistsException(BaseServiceException):
    """Role already exists exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Role already exists"
        super().__init__(message, "ROLE_ALREADY_EXISTS", details, status_code=409, log_level="warning")

class WebPushSubscriptionNotFoundException(BaseServiceException):
    """Web push subscription not found exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Web push subscription not found"
        super().__init__(message, "WEB_PUSH_SUBSCRIPTION_NOT_FOUND", details, status_code=404, log_level="warning")

class ModbusConnectionException(BaseServiceException):
    """Modbus connection failed exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Modbus connection failed"
        super().__init__(message, "MODBUS_CONNECTION_FAILED", details, status_code=400, log_level="warning")

class ModbusControllerNotFoundException(BaseServiceException):
    """Modbus controller not found exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Modbus controller not found"
        super().__init__(message, "MODBUS_CONTROLLER_NOT_FOUND", details, status_code=404, log_level="warning")

class ModbusPointNotFoundException(BaseServiceException):
    """Modbus point not found exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Modbus point not found"
        super().__init__(message, "MODBUS_POINT_NOT_FOUND", details, status_code=404, log_level="warning")

class ModbusReadException(BaseServiceException):
    """Modbus read operation failed"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Modbus read operation failed"
        super().__init__(message, "MODBUS_READ_FAILED", details, status_code=400, log_level="warning")


class ModbusWriteException(BaseServiceException):
    """Modbus write operation failed"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Modbus write operation failed"
        super().__init__(message, "MODBUS_WRITE_FAILED", details, status_code=400, log_level="warning")


class ModbusRangeValidationException(BaseServiceException):
    """Modbus range validation failed"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Value is outside the valid range"
        super().__init__(message, "MODBUS_RANGE_VALIDATION_FAILED", details, status_code=422, log_level="warning")


class ModbusValidationException(BaseServiceException):
    """Modbus validation failed exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Modbus validation failed"
        super().__init__(message, "MODBUS_VALIDATION_FAILED", details, status_code=409, log_level="warning")

class ModbusControllerDisconnectedException(BaseServiceException):
    """Modbus controller is disconnected exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Modbus controller is disconnected"
        super().__init__(message, "MODBUS_CONTROLLER_DISCONNECTED", details, status_code=400, log_level="warning")

class ModbusConfigException(BaseServiceException):
    """Modbus configuration exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Modbus configuration error"
        super().__init__(message, "MODBUS_CONFIG_ERROR", details, status_code=400, log_level="error")

class ModbusConfigFormatException(BaseServiceException):
    """Modbus configuration format exception"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Configuration format error"
        super().__init__(message, "MODBUS_CONFIG_FORMAT_ERROR", details, status_code=415, log_level="warning")

class ModbusControllerDuplicateException(BaseServiceException):
    """Modbus controller with same host and port already exists"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Controller with same host and port already exists"
        super().__init__(message, "MODBUS_CONTROLLER_DUPLICATE", details, status_code=409, log_level="warning")

class ModbusPointDuplicateException(BaseServiceException):
    """Modbus point with same unit_id, address, and type already exists"""
    def __init__(self, message: str = None, details: Dict[str, Any] = None):
        message = f"{message}" if message else "Point with same unit_id, address, and type already exists"
        super().__init__(message, "MODBUS_POINT_DUPLICATE", details, status_code=409, log_level="warning")