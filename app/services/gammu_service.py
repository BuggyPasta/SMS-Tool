"""
Gammu service for SMS functionality
"""

import gammu
import logging
import os
import threading
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

    def get_modem_info(self) -> Dict[str, Any]:
        """Get comprehensive modem information"""
        logger.debug("Getting modem information")
        try:
            if not self.connected:
                self.connect()
            
            info = {
                'security': self.state_machine.GetSecurityStatus(),
                'signal': self.state_machine.GetSignalQuality(),
                'battery': self.state_machine.GetBatteryCharge(),
                'manufacturer': self.state_machine.GetManufacturer(),
                'model': self.state_machine.GetModel()
            }
            return info
        except Exception as e:
            logger.error(f"Failed to get modem info: {e}")
            raise ModemError(f"Failed to get modem info: {str(e)}", ErrorCode.MODEM_STATUS_ERROR)

    def get_sim_status(self) -> Dict[str, Any]:
        """Get SIM card status"""
        logger.debug("Getting SIM status")
        try:
            if not self.connected:
                self.connect()
            
            return {
                'imsi': self.state_machine.GetSIMIMSI(),
                'status': self.state_machine.GetSIMStatus()
            }
        except gammu.ERR_SECURITYERROR:
            logger.error("SIM card locked")
            raise SIMError("SIM card is locked", ErrorCode.SIM_LOCKED)
        except gammu.ERR_INVALIDSIMCARD:
            logger.error("Invalid SIM card")
            raise SIMError("Invalid SIM card", ErrorCode.SIM_INVALID)
        except Exception as e:
            logger.error(f"Failed to get SIM status: {e}")
            raise SIMError(f"Failed to get SIM status: {str(e)}", ErrorCode.SIM_STATUS_ERROR)

    def get_network_status(self) -> Dict[str, Any]:
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