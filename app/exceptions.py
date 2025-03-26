"""
Custom exceptions for the SMS Tool application
"""

from typing import Optional, Dict, Any
import logging
from enum import Enum

logger = logging.getLogger('app')

class ErrorCode(Enum):
    """Error codes for different types of errors"""
    # General errors (1000-1999)
    UNKNOWN_ERROR = 1000
    CONFIGURATION_ERROR = 1001
    
    # Device errors (2000-2999)
    DEVICE_NOT_FOUND = 2000
    DEVICE_PERMISSION_DENIED = 2001
    DEVICE_BUSY = 2002
    DEVICE_ACCESS_ERROR = 2003
    
    # Modem errors (3000-3999)
    MODEM_NOT_RESPONDING = 3000
    MODEM_INITIALIZATION_FAILED = 3001
    MODEM_CONNECTION_FAILED = 3002
    
    # SIM errors (4000-4999)
    SIM_NOT_DETECTED = 4000
    SIM_PIN_REQUIRED = 4001
    SIM_PUK_REQUIRED = 4002
    
    # Network errors (5000-5999)
    NETWORK_NOT_REGISTERED = 5000
    NETWORK_REGISTRATION_DENIED = 5001
    NETWORK_TIMEOUT = 5002
    
    # Message errors (6000-6999)
    MESSAGE_SEND_FAILED = 6000
    MESSAGE_INVALID_FORMAT = 6001
    MESSAGE_QUEUE_FULL = 6002

class SMSToolException(Exception):
    """Base exception class for SMS Tool"""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.original_error = original_error
        
        # Log the error
        self._log_error()
    
    def _log_error(self) -> None:
        """Log the error with appropriate context"""
        error_info = {
            'error_code': self.error_code.name,
            'error_number': self.error_code.value,
            'message': str(self),
            'details': self.details
        }
        
        if self.original_error:
            error_info['original_error'] = {
                'type': type(self.original_error).__name__,
                'message': str(self.original_error)
            }
        
        logger.error(f"Exception occurred: {error_info}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format for API responses"""
        return {
            'error': {
                'code': self.error_code.name,
                'number': self.error_code.value,
                'message': str(self),
                'details': self.details
            }
        }

class GammuError(SMSToolException):
    """Base exception for Gammu-related errors"""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, original_error)

class ModemError(GammuError):
    """Exception raised for modem-related errors"""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.MODEM_NOT_RESPONDING,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, original_error)

class SIMError(GammuError):
    """Exception raised for SIM card-related errors"""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.SIM_NOT_DETECTED,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, original_error)

class NetworkError(GammuError):
    """Exception raised for network connectivity issues"""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.NETWORK_NOT_REGISTERED,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, original_error)

class ConfigError(GammuError):
    """Exception raised for configuration-related errors"""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.CONFIGURATION_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, original_error)

class DeviceError(GammuError):
    """Exception raised for device access or permission errors"""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DEVICE_NOT_FOUND,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, original_error) 