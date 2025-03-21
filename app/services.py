"""
Business logic and services
"""

import gammu
import logging
import os
from datetime import datetime
import pytz
from .config import Config
from .models import Message
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom Exception Classes
class GammuError(Exception):
    """Base exception for Gammu-related errors"""
    pass

class ModemError(GammuError):
    """Exception raised for modem-related errors"""
    pass

class SIMError(GammuError):
    """Exception raised for SIM card-related errors"""
    pass

class NetworkError(GammuError):
    """Exception raised for network-related errors"""
    pass

class GammuService:
    _instance = None
    _lock = threading.Lock()
    _is_connected = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super(GammuService, cls).__new__(cls)
                    cls._instance.state_machine = None
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

    def connect(self):
        """Connect to the modem"""
        with self._lock:
            if self._is_connected:
                logger.info("Already connected to modem")
                return

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
                    import grp
                    dialout_gid = grp.getgrnam('dialout').gr_gid
                    logger.info(f"Dialout group ID: {dialout_gid}")
                    if gid != dialout_gid and dialout_gid not in groups:
                        error_msg = "User is not in the dialout group"
                        logger.error(error_msg)
                        raise ModemError(error_msg)
                    logger.info("User has proper dialout group membership")
                except ImportError:
                    logger.warning("Could not import grp module - skipping group check")
                except KeyError:
                    logger.warning("Dialout group not found - skipping group check")
                except Exception as e:
                    logger.error(f"Error checking dialout group: {e}")
                    raise ModemError(f"Group permission check failed: {e}")

                # Check device existence and permissions
                if not os.path.exists('/dev/ttyUSB3'):
                    error_msg = "Device /dev/ttyUSB3 does not exist"
                    logger.error(error_msg)
                    raise ModemError(error_msg)

                try:
                    stat = os.stat('/dev/ttyUSB3')
                    mode = stat.st_mode & 0o777  # Get only permission bits
                    logger.info(f"Device permissions: {oct(mode)}")
                    
                    # Check if device is readable and writable by group
                    if not (mode & 0o060):  # Check for group read/write
                        error_msg = f"Insufficient group permissions on /dev/ttyUSB3: {oct(mode)}"
                        logger.error(error_msg)
                        raise ModemError(error_msg)
                    
                    logger.info("Device has proper permissions")
                except OSError as e:
                    error_msg = f"Cannot access device permissions: {e}"
                    logger.error(error_msg)
                    raise ModemError(error_msg)

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
                        error_msg = f"Failed to read config from file: {config_e}"
                        logger.error(error_msg)
                        raise ModemError(error_msg)
                
                # Initialize the connection with retries
                max_retries = 3
                last_error = None
                for attempt in range(max_retries):
                    try:
                        logger.info(f"Attempting to initialize connection (attempt {attempt + 1}/{max_retries})...")
                        self.state_machine.Init()
                        logger.info("Successfully connected to modem")
                        self._is_connected = True
                        break
                    except Exception as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                            import time
                            time.sleep(2)  # Wait before retry
                        else:
                            error_msg = f"Failed to initialize modem after {max_retries} attempts: {e}"
                            logger.error(error_msg)
                            raise ModemError(error_msg)
                
                # Get basic modem info for diagnostics
                if self._is_connected:
                    try:
                        manufacturer = self.state_machine.GetManufacturer()
                        model = self.state_machine.GetModel()
                        logger.info(f"Connected to {manufacturer} {model}")
                    except Exception as e:
                        logger.warning(f"Could not get modem details: {e}")
                
            except ModemError:
                self._is_connected = False
                self.state_machine = None
                raise
            except Exception as e:
                self._is_connected = False
                self.state_machine = None
                logger.error(f"Unexpected error during connection: {e}")
                if hasattr(e, '__dict__'):
                    logger.error(f"Error attributes: {e.__dict__}")
                raise ModemError(f"Failed to connect to modem: {e}")

    def send_sms(self, phone_number, message, message_id):
        """Send SMS message"""
        with self._lock:
            if not self.is_connected():
                logger.error("Cannot send SMS: not connected to modem")
                Message.update_status(message_id, 'failed', "Not connected to modem")
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
                logger.error(f"Failed to send message {message_id}: {str(e)}")
                Message.update_status(message_id, 'failed', str(e))
                return False

    def check_modem_status(self):
        """Check modem status and network registration"""
        with self._lock:
            if not self.is_connected():
                logger.error("Cannot check modem status: not connected")
                return False
            try:
                status = self.state_machine.GetNetworkInfo()
                return status['NetworkCode'] != 0
            except Exception as e:
                logger.error(f"Failed to check modem status: {str(e)}")
                return False

    def get_signal_strength(self):
        """Get signal strength"""
        with self._lock:
            if not self.is_connected():
                logger.error("Cannot get signal strength: not connected")
                return 0
            try:
                status = self.state_machine.GetSignalQuality()
                return status['SignalPercent']
            except Exception as e:
                logger.error(f"Failed to get signal strength: {str(e)}")
                return 0

    def get_battery_status(self):
        """Get battery status"""
        with self._lock:
            if not self.is_connected():
                logger.error("Cannot get battery status: not connected")
                return 0
            try:
                status = self.state_machine.GetBatteryCharge()
                return status['BatteryPercent']
            except Exception as e:
                logger.error(f"Failed to get battery status: {str(e)}")
                return 0

    def get_sim_status(self):
        """Get SIM card status"""
        with self._lock:
            if not self.is_connected():
                logger.error("Cannot get SIM status: not connected")
                return None
            try:
                status = self.state_machine.GetSIMStatus()
                return status['SIMStatus']
            except Exception as e:
                logger.error(f"Failed to get SIM status: {str(e)}")
                return None

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

    def is_connected(self):
        """Check if the service is connected to the modem"""
        with self._lock:
            return self._is_connected and self.state_machine is not None 