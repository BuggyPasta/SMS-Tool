"""
Gammu service for SMS functionality
"""

import gammu
import logging
import os
import re
from datetime import datetime
import pytz
from .config import Config
from .models import Message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/gammu.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ModemError(Exception):
    """Raised when there are issues with the modem"""
    pass

class SIMError(Exception):
    """Raised when there are issues with the SIM card"""
    pass

class NetworkError(Exception):
    """Raised when there are network connectivity issues"""
    pass

class GammuError(Exception):
    """Raised for general Gammu-related errors"""
    pass

class GammuService:
    def __init__(self):
        self.state_machine = None
        self.connect()

    def _log_error(self, error_type, message, details=None):
        """Log error with detailed system state"""
        system_state = {
            'modem_status': self._get_modem_status(),
            'sim_status': self._get_sim_status(),
            'network_status': self._get_network_status(),
            'message_queue_size': self._get_message_queue_size()
        }
        
        logger.error(f"{error_type}: {message}")
        if details:
            logger.error(f"Details: {details}")
        logger.error(f"System state: {system_state}")

    def _get_modem_status(self):
        """Get current modem status"""
        try:
            if not self.state_machine:
                return "Not connected"
            return self.state_machine.GetSignalQuality()
        except:
            return "Unknown"

    def _get_sim_status(self):
        """Get current SIM card status"""
        try:
            if not self.state_machine:
                return "Not connected"
            return self.state_machine.GetSIMStatus()
        except:
            return "Unknown"

    def _get_network_status(self):
        """Get current network status"""
        try:
            if not self.state_machine:
                return "Not connected"
            return self.state_machine.GetNetworkInfo()
        except:
            return "Unknown"

    def _get_message_queue_size(self):
        """Get current message queue size"""
        try:
            if not self.state_machine:
                return 0
            return len(self.state_machine.GetSMSStatus())
        except:
            return 0

    def connect(self):
        """Connect to the modem"""
        try:
            if not os.path.exists(Config.GAMMU_CONFIG):
                raise GammuError("Gammu configuration file not found")
            
            self.state_machine = gammu.StateMachine()
            self.state_machine.ReadConfig(Config.GAMMU_CONFIG)
            self.state_machine.Init()
            
            # Verify modem connection
            if not self._get_modem_status():
                raise ModemError("Modem not responding")
            
            # Verify SIM card
            if not self._get_sim_status():
                raise SIMError("SIM card not detected")
            
            # Verify network registration
            if not self._get_network_status():
                raise NetworkError("Not registered on network")
            
            logger.info("Successfully connected to modem")
        except Exception as e:
            self._log_error("Connection Error", str(e))
            raise

    def _sanitize_message(self, message):
        """Sanitize message content"""
        try:
            # Character encoding check
            message.encode('ascii', 'strict')
            
            # Check for repeated characters
            if re.search(r'(.)\1{3,}', message):
                raise ValueError("Message contains too many repeated characters")
            
            # Remove control characters
            message = ''.join(char for char in message if char.isprintable())
            
            # Format for injection prevention
            message = message.replace('"', '\\"')
            
            return message
        except UnicodeEncodeError:
            raise ValueError("Message contains unsupported characters")
        except Exception as e:
            raise ValueError(f"Message sanitization failed: {str(e)}")

    def send_sms(self, phone_number, message, message_id):
        """Send SMS message"""
        try:
            # Check message queue
            if self._get_message_queue_size() >= 100:
                raise GammuError("Message queue is full")
            
            # Format phone number
            phone_number = ''.join(filter(str.isdigit, phone_number))
            if not phone_number.startswith('07') or len(phone_number) != 11:
                raise ValueError("Invalid UK mobile number format")
            
            # Sanitize message
            message = self._sanitize_message(message)
            
            # Update status to sending
            Message.update_status(message_id, 'sending')
            
            # Create message structure
            message_data = {
                'Text': message,
                'SMSC': {'Location': 1},
                'Number': phone_number,
            }

            # Send message
            self.state_machine.SendSMS(message_data)
            logger.info(f"Message {message_id} sent successfully to {phone_number}")
            
            # Update status to sent
            Message.update_status(message_id, 'sent')
            return True

        except ModemError as e:
            self._log_error("Modem Error", str(e))
            Message.update_status(message_id, 'failed', str(e))
            raise
        except SIMError as e:
            self._log_error("SIM Error", str(e))
            Message.update_status(message_id, 'failed', str(e))
            raise
        except NetworkError as e:
            self._log_error("Network Error", str(e))
            Message.update_status(message_id, 'failed', str(e))
            raise
        except ValueError as e:
            self._log_error("Validation Error", str(e))
            Message.update_status(message_id, 'failed', str(e))
            raise
        except Exception as e:
            self._log_error("Gammu Error", str(e))
            Message.update_status(message_id, 'failed', str(e))
            raise

    def disconnect(self):
        """Disconnect from the modem"""
        try:
            if self.state_machine:
                self.state_machine.Terminate()
                self.state_machine = None
                logger.info("Successfully disconnected from modem")
        except Exception as e:
            self._log_error("Disconnect Error", str(e))
            raise 