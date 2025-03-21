"""
Gammu service for SMS functionality
"""

import gammu
import logging
import os
import threading
import grp
from datetime import datetime, timedelta
import time
from typing import Dict, Any, Optional
from ..config import Config
from ..models import Message
from ..exceptions import (
    ErrorCode,
    GammuError,
    ModemError,
    SIMError,
    NetworkError,
    ConfigError,
    DeviceError
)

# Get logger
logger = logging.getLogger('gammu')

class ConnectionState:
    """Thread-safe connection state cache"""
    def __init__(self, cache_duration: int = 5):
        self.lock = threading.Lock()
        self._cache_duration = cache_duration  # seconds
        self._reset()
    
    def _reset(self) -> None:
        """Reset all cached values"""
        self._modem_status = None
        self._signal_strength = None
        self._battery_status = None
        self._sim_status = None
        self._last_update = None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self._last_update is None:
            return False
        return (datetime.now() - self._last_update) < timedelta(seconds=self._cache_duration)
    
    def update(self, **kwargs) -> None:
        """Update cached values"""
        with self.lock:
            for key, value in kwargs.items():
                setattr(self, f"_{key}", value)
            self._last_update = datetime.now()
    
    def get(self, key: str) -> Any:
        """Get cached value if valid, otherwise return None"""
        with self.lock:
            if self._is_cache_valid():
                return getattr(self, f"_{key}")
            return None
    
    def invalidate(self) -> None:
        """Invalidate all cached values"""
        with self.lock:
            self._reset()

class GammuService:
    """Thread-safe singleton service for Gammu SMS functionality"""
    _instance = None
    _lock = threading.Lock()
    _is_connected = False
    _connection_timeout = 30  # seconds

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super(GammuService, cls).__new__(cls)
                    cls._instance.state_machine = None
                    cls._instance._state = ConnectionState()
        return cls._instance

    def __init__(self):
        with self._lock:
            if not self._is_connected:
                self.connect()

    def __del__(self):
        """Ensure cleanup when instance is destroyed"""
        try:
            self.close()
        except Exception as e:
            logger.error(f"Error during cleanup in __del__: {e}")

    def _get_cached_state(self, key: str, fetch_func, error_code: ErrorCode) -> Any:
        """Get state from cache or fetch and cache it"""
        try:
            value = self._state.get(key)
            if value is not None:
                return value
                
            with self._lock:
                if not self._is_connected:
                    raise ModemError("Modem is not connected", error_code)
                    
                try:
                    value = fetch_func()
                    self._state.update(**{key: value})
                    return value
                except gammu.GSMError as e:
                    self._state.invalidate()
                    raise ModemError(f"Failed to fetch {key}: {str(e)}", error_code) from e
                    
        except Exception as e:
            if not isinstance(e, ModemError):
                self._state.invalidate()
                raise ModemError(f"Unexpected error fetching {key}: {str(e)}", error_code) from e
            raise

    def is_connected(self) -> bool:
        """Check if the service is connected to the modem"""
        with self._lock:
            return self._is_connected and self.state_machine is not None

    def connect(self):
        """Connect to the modem"""
        with self._lock:
            if self._is_connected:
                logger.info("Already connected to modem")
                return

            connect_start = time.time()
            try:
                # Log current user and permissions
                uid = os.getuid()
                gid = os.getgid()
                groups = os.getgroups()
                logger.info(f"Current user ID: {uid}")
                logger.info(f"Current group ID: {gid}")
                logger.info(f"Supplementary groups: {groups}")
                
                # Check dialout group membership
                try:
                    dialout_gid = grp.getgrnam('dialout').gr_gid
                    logger.info(f"Dialout group ID: {dialout_gid}")
                    if gid != dialout_gid and dialout_gid not in groups:
                        raise DeviceError(
                            "User is not in the dialout group",
                            error_code=ErrorCode.DEVICE_PERMISSION_DENIED,
                            details={'uid': uid, 'gid': gid, 'groups': groups}
                        )
                except ImportError:
                    logger.warning("Could not import grp module - skipping group check")
                except KeyError:
                    logger.warning("Dialout group not found - skipping group check")
                except Exception as e:
                    raise DeviceError(
                        "Group permission check failed",
                        error_code=ErrorCode.DEVICE_PERMISSION_DENIED,
                        original_error=e
                    )

                # Check device existence and permissions
                if not os.path.exists('/dev/ttyUSB3'):
                    raise DeviceError(
                        "Device /dev/ttyUSB3 does not exist",
                        error_code=ErrorCode.DEVICE_NOT_FOUND
                    )

                try:
                    stat = os.stat('/dev/ttyUSB3')
                    mode = stat.st_mode & 0o777
                    logger.info(f"Device permissions: {oct(mode)}")
                    
                    if not (mode & 0o060):
                        raise DeviceError(
                            f"Insufficient group permissions on /dev/ttyUSB3: {oct(mode)}",
                            error_code=ErrorCode.DEVICE_PERMISSION_DENIED,
                            details={'mode': oct(mode)}
                        )
                    
                    logger.info("Device has proper permissions")
                except OSError as e:
                    raise DeviceError(
                        "Cannot access device permissions",
                        error_code=ErrorCode.DEVICE_ACCESS_ERROR,
                        original_error=e
                    )

                # Initialize state machine if not already initialized
                if self.state_machine is None:
                    self.state_machine = gammu.StateMachine()
                    logger.info("State machine created")
                
                # Use minimal configuration
                debug_config = {
                    'Device': '/dev/ttyUSB3',
                    'Connection': 'at',
                    'Model': 'auto'
                }
                
                # Try setting config directly
                logger.info("Setting Gammu configuration programmatically")
                try:
                    self.state_machine.SetConfig(0, debug_config)
                    logger.info("Config set successfully")
                except Exception as e:
                    logger.error(f"Failed to set config programmatically: {e}")
                    # Fall back to reading from file
                    logger.info("Falling back to reading config from /etc/gammurc")
                    try:
                        self.state_machine.ReadConfig(Filename='/etc/gammurc')
                        logger.info("Config read successfully from file")
                    except Exception as config_e:
                        raise ConfigError(
                            "Failed to read config from file",
                            error_code=ErrorCode.CONFIGURATION_ERROR,
                            original_error=config_e
                        )
                
                # Initialize the connection with retries
                max_retries = 3
                last_error = None
                for attempt in range(max_retries):
                    try:
                        if time.time() - connect_start > self._connection_timeout:
                            raise ModemError(
                                "Connection timeout",
                                error_code=ErrorCode.MODEM_CONNECTION_FAILED,
                                details={'timeout': self._connection_timeout}
                            )
                            
                        logger.info(f"Attempting to initialize connection (attempt {attempt + 1}/{max_retries})...")
                        self.state_machine.Init()
                        logger.info("Successfully connected to modem")
                        self._is_connected = True
                        break
                    except Exception as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                            time.sleep(2)
                        else:
                            raise ModemError(
                                f"Failed to initialize modem after {max_retries} attempts",
                                error_code=ErrorCode.MODEM_INITIALIZATION_FAILED,
                                original_error=last_error
                            )
                
                # Get basic modem info for diagnostics
                if self._is_connected:
                    try:
                        manufacturer = self.state_machine.GetManufacturer()
                        model = self.state_machine.GetModel()
                        logger.info(f"Connected to {manufacturer} {model}")
                        
                        # Initialize connection state
                        self._state.update(
                            modem_status=self.check_modem_status(),
                            signal_strength=self.get_signal_strength(),
                            battery_status=self.get_battery_status(),
                            sim_status=self.get_sim_status()
                        )
                    except Exception as e:
                        logger.warning(f"Could not get modem details: {e}")
                
            except (ModemError, DeviceError, ConfigError) as e:
                self._is_connected = False
                self.state_machine = None
                self._state.invalidate()
                raise
            except Exception as e:
                self._is_connected = False
                self.state_machine = None
                self._state.invalidate()
                raise ModemError(
                    "Failed to connect to modem",
                    error_code=ErrorCode.MODEM_CONNECTION_FAILED,
                    original_error=e
                )

    def send_sms(self, phone_number: str, message: str, message_id: int) -> bool:
        """Send SMS message"""
        with self._lock:
            if not self.is_connected():
                error_msg = "Cannot send SMS: not connected to modem"
                logger.error(error_msg)
                Message.update_status(message_id, 'failed', error_msg)
                return False

            try:
                # Format phone number (remove any non-digit characters)
                phone_number = ''.join(filter(str.isdigit, phone_number))
                
                # Create message structure
                message_data = {
                    'Text': message,
                    'SMSC': {'Location': 1},
                    'Number': phone_number,
                }

                # Send message
                self.state_machine.SendSMS(message_data)
                logger.info(f"Message {message_id} sent successfully to {phone_number}")
                
                # Update message status
                Message.update_status(message_id, 'sent')
                return True

            except Exception as e:
                error_msg = f"Failed to send message {message_id}: {str(e)}"
                logger.error(error_msg, extra={
                    'phone_number': phone_number,
                    'message_id': message_id,
                    'error': str(e)
                })
                Message.update_status(message_id, 'failed', str(e))
                return False

    def check_modem_status(self) -> bool:
        """Check modem status and network registration"""
        def fetch_status():
            status = self.state_machine.GetNetworkInfo()
            return status['NetworkCode'] != 0
            
        return self._get_cached_state(
            'modem_status',
            fetch_status,
            ErrorCode.MODEM_NOT_RESPONDING
        )

    def get_signal_strength(self) -> int:
        """Get signal strength"""
        def fetch_signal():
            status = self.state_machine.GetSignalQuality()
            return status['SignalPercent']
            
        return self._get_cached_state(
            'signal_strength',
            fetch_signal,
            ErrorCode.MODEM_NOT_RESPONDING
        )

    def get_battery_status(self) -> int:
        """Get battery status"""
        def fetch_battery():
            status = self.state_machine.GetBatteryCharge()
            return status['BatteryPercent']
            
        return self._get_cached_state(
            'battery_status',
            fetch_battery,
            ErrorCode.MODEM_NOT_RESPONDING
        )

    def get_sim_status(self) -> Optional[str]:
        """Get SIM card status"""
        def fetch_sim():
            status = self.state_machine.GetSIMStatus()
            return status['SIMStatus']
            
        return self._get_cached_state(
            'sim_status',
            fetch_sim,
            ErrorCode.SIM_NOT_DETECTED
        )

    def close(self):
        """Close connection to modem"""
        with self._lock:
            if self.state_machine and self._is_connected:
                try:
                    self.state_machine.Terminate()
                    logger.info("Modem connection closed")
                except Exception as e:
                    logger.error(f"Error closing modem connection: {e}")
                finally:
                    self._is_connected = False
                    self.state_machine = None
                    self._state.invalidate() 