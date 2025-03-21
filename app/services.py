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
            # Create Gammu configuration with only essential settings
            gammu_config = {
                'Device': '/dev/ttyUSB3',
                'Connection': 'at'
            }
            
            # Initialize state machine
            self.state_machine = gammu.StateMachine()
            
            # Set configuration programmatically
            self.state_machine.SetConfig(0, gammu_config)
            
            # Initialize the connection
            self.state_machine.Init()
            logger.info("Successfully connected to modem")
        except Exception as e:
            logger.error(f"Failed to connect to modem: {str(e)}")
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