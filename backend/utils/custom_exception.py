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
