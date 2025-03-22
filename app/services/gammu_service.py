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

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GammuService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize Gammu service"""
        with self._lock:
            if self._initialized:
                return
                
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
            except Exception as e:
                logger.error(f"Failed to initialize GammuService: {e}")
                raise GammuError(f"Failed to initialize Gammu: {str(e)}", ErrorCode.GAMMU_INIT_FAILED)
            
            self._initialized = True

    def __del__(self):
        """Ensure cleanup when instance is destroyed"""
        self.disconnect()

    def connect(self) -> bool:
        """Connect to the modem"""
        with self._lock:
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
        with self._lock:
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

    def is_connected(self) -> bool:
        """Check if connected to modem"""
        with self._lock:
            return self.connected and self.state_machine is not None

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

    def send_sms(self, phone_number: str, message: str, message_id: Optional[int] = None) -> bool:
        """Send SMS message"""
        logger.info(f"Sending SMS to {phone_number}")
        try:
            if not self.connected:
                self.connect()

            # Prepare message data
            message_data = {
                'Text': message,
                'SMSC': {'Location': 1},
                'Number': phone_number
            }

            # Send message
            logger.debug("Sending message")
            self.state_machine.SendSMS(message_data)
            logger.info(f"Successfully sent SMS to {phone_number}")
            return True

        except gammu.ERR_EMPTY:
            logger.error("Empty message")
            raise ValueError("Message cannot be empty")
        except gammu.ERR_INVALIDLOCATION:
            logger.error("Invalid number")
            raise ValueError("Invalid phone number")
        except gammu.ERR_NETWORK_ERROR:
            logger.error("Network error")
            raise NetworkError("Failed to send SMS: Network error", ErrorCode.NETWORK_ERROR)
        except gammu.ERR_TIMEOUT:
            logger.error("Operation timed out")
            raise NetworkError("Failed to send SMS: Timeout", ErrorCode.NETWORK_TIMEOUT)
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            raise GammuError(f"Failed to send SMS: {str(e)}", ErrorCode.SMS_SEND_ERROR)

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