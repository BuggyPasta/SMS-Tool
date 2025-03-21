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
    def __init__(self):
        self.state_machine = None
        self.connect()

    def connect(self):
        """Connect to the modem"""
        try:
            # Log current user and permissions
            uid = os.getuid()
            gid = os.getgid()
            groups = os.getgroups()
            logger.info(f"Current user ID: {uid}")
            logger.info(f"Current group ID: {gid}")
            logger.info(f"Supplementary groups: {groups}")
            
            try:
                import grp
                dialout_gid = grp.getgrnam('dialout').gr_gid
                logger.info(f"Dialout group ID: {dialout_gid}")
                if gid == dialout_gid:
                    logger.info("Primary group is dialout")
                if dialout_gid in groups:
                    logger.info("User has dialout in supplementary groups")
            except Exception as e:
                logger.error(f"Error checking dialout group: {e}")

            if os.path.exists('/dev/ttyUSB3'):
                stat = os.stat('/dev/ttyUSB3')
                logger.info(f"Device exists and has mode: {oct(stat.st_mode)}")
                logger.info(f"Device owner: uid={stat.st_uid}, gid={stat.st_gid}")
                
                # Try to open device directly first
                try:
                    import fcntl
                    import termios
                    fd = os.open('/dev/ttyUSB3', os.O_RDWR | os.O_NOCTTY)
                    logger.info("Successfully opened device directly")
                    
                    # Try to get exclusive lock
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    logger.info("Successfully obtained device lock")
                    
                    # Try basic serial port configuration
                    attrs = termios.tcgetattr(fd)
                    logger.info("Successfully got terminal attributes")
                    os.close(fd)
                except Exception as e:
                    logger.error(f"Error in direct device access: {e}")
                    if 'fd' in locals():
                        try:
                            os.close(fd)
                        except:
                            pass
                    raise
            else:
                logger.info("Device /dev/ttyUSB3 does not exist")

            # Initialize state machine
            self.state_machine = gammu.StateMachine()
            logger.info("State machine created")
            
            # Read configuration from gammurc
            logger.info("Reading config from /etc/gammurc")
            with open('/etc/gammurc', 'r') as f:
                logger.info(f"gammurc contents:\n{f.read()}")
            self.state_machine.ReadConfig(Filename='/etc/gammurc')
            logger.info("Config read successfully")
            
            # Initialize the connection
            logger.info("Attempting to initialize connection...")
            self.state_machine.Init()
            logger.info("Successfully connected to modem")
        except Exception as e:
            logger.error(f"Failed to connect to modem: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            if hasattr(e, '__dict__'):
                logger.error(f"Error attributes: {e.__dict__}")
            raise ModemError(f"Failed to connect to modem: {str(e)}")

    def send_sms(self, phone_number, message, message_id):
        """Send SMS message"""
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
            Message.update_status(message_id, 'failed')
            return False

    def check_modem_status(self):
        """Check modem status and network registration"""
        try:
            status = self.state_machine.GetNetworkInfo()
            return status['NetworkCode'] != 0
        except Exception as e:
            logger.error(f"Failed to check modem status: {str(e)}")
            return False

    def get_signal_strength(self):
        """Get signal strength"""
        try:
            status = self.state_machine.GetSignalQuality()
            return status['SignalPercent']
        except Exception as e:
            logger.error(f"Failed to get signal strength: {str(e)}")
            return 0

    def get_battery_status(self):
        """Get battery status"""
        try:
            status = self.state_machine.GetBatteryCharge()
            return status['BatteryPercent']
        except Exception as e:
            logger.error(f"Failed to get battery status: {str(e)}")
            return 0

    def get_sim_status(self):
        """Get SIM card status"""
        try:
            status = self.state_machine.GetSIMStatus()
            return status['SIMStatus']
        except Exception as e:
            logger.error(f"Failed to get SIM status: {str(e)}")
            return None

    def close(self):
        """Close connection to modem"""
        if self.state_machine:
            self.state_machine.Terminate()
            logger.info("Modem connection closed") 