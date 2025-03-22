"""
Gammu service for SMS functionality
"""

import gammu
import logging
import os
import threading
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
        """Initialize Gammu service"""
        logger.info("Initializing GammuService")
        self.state_machine = None
        self.connected = False
        try:
            logger.debug("Creating Gammu state machine")
            self.state_machine = gammu.StateMachine()
            logger.debug("Reading Gammu config")
            self.state_machine.ReadConfig(Filename='/etc/gammurc')
            logger.info("Successfully initialized GammuService")
        except gammu.ERR_NONE:
            logger.warning("Gammu initialization warning, but continuing")
            pass
        except Exception as e:
            logger.error(f"Failed to initialize GammuService: {e}")
            raise GammuError(f"Failed to initialize Gammu: {str(e)}", ErrorCode.GAMMU_INIT_FAILED)

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
        if self.connected:
            logger.debug("Already connected")
            return True

        logger.info("Connecting to modem")
        try:
            logger.debug("Attempting to initialize state machine")
            self.state_machine.Init()
            self.connected = True
            logger.info("Successfully connected to modem")
            return True
        except gammu.ERR_DEVICENOTEXIST:
            logger.error("Modem device not found")
            raise ModemError("Modem device not found", ErrorCode.MODEM_NOT_FOUND)
        except gammu.ERR_DEVICEBUSY:
            logger.error("Modem device is busy")
            raise ModemError("Modem device is busy", ErrorCode.MODEM_BUSY)
        except gammu.ERR_DEVICEOPENERROR:
            logger.error("Failed to open modem device")
            raise ModemError("Failed to open modem device", ErrorCode.MODEM_OPEN_ERROR)
        except Exception as e:
            logger.error(f"Failed to connect to modem: {e}")
            raise ModemError(f"Failed to connect to modem: {str(e)}", ErrorCode.MODEM_CONNECT_ERROR)

    def disconnect(self):
        """Disconnect from the modem"""
        if not self.connected:
            logger.debug("Already disconnected")
            return

        logger.info("Disconnecting from modem")
        try:
            self.state_machine.Terminate()
            self.connected = False
            logger.info("Successfully disconnected from modem")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            # Don't raise here as we're likely cleaning up

    def get_modem_status(self):
        """Get modem status information"""
        logger.debug("Getting modem status")
        try:
            if not self.connected:
                self.connect()
            return self.state_machine.GetSecurityStatus()
        except Exception as e:
            logger.error(f"Failed to get modem status: {e}")
            raise ModemError(f"Failed to get modem status: {str(e)}", ErrorCode.MODEM_STATUS_ERROR)

    def get_sim_status(self):
        """Get SIM card status"""
        logger.debug("Getting SIM status")
        try:
            if not self.connected:
                self.connect()
            return self.state_machine.GetSIMIMSI()
        except gammu.ERR_SECURITYERROR:
            logger.error("SIM card locked")
            raise SIMError("SIM card is locked", ErrorCode.SIM_LOCKED)
        except gammu.ERR_INVALIDSIMCARD:
            logger.error("Invalid SIM card")
            raise SIMError("Invalid SIM card", ErrorCode.SIM_INVALID)
        except Exception as e:
            logger.error(f"Failed to get SIM status: {e}")
            raise SIMError(f"Failed to get SIM status: {str(e)}", ErrorCode.SIM_STATUS_ERROR)

    def get_network_status(self):
        """Get network status"""
        logger.debug("Getting network status")
        try:
            if not self.connected:
                self.connect()
            return self.state_machine.GetNetworkInfo()
        except Exception as e:
            logger.error(f"Failed to get network status: {e}")
            raise NetworkError(f"Failed to get network status: {str(e)}", ErrorCode.NETWORK_STATUS_ERROR)

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