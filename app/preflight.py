#!/usr/bin/env python3
"""
Preflight checks for SMS Tool
"""

import os
import sys
import gammu
import logging
from .logging_config import setup_logging

# Set up logging
loggers = setup_logging()
logger = loggers['app']

def check_device_exists():
    """Check if the USB device exists"""
    if not os.path.exists('/dev/ttyUSB3'):
        logger.error("❌ Device /dev/ttyUSB3 does not exist")
        return False
    logger.info("✓ Device exists")
    return True

def check_gammu_config():
    """Check if Gammu config is readable and valid"""
    try:
        if not os.path.exists('/etc/gammurc'):
            logger.error("❌ Gammu config file does not exist")
            return False
        
        # Try to read config without initializing
        sm = gammu.StateMachine()
        sm.ReadConfig(Filename='/etc/gammurc')
        logger.info("✓ Gammu config is valid")
        return True
    except Exception as e:
        logger.error(f"❌ Error checking Gammu config: {e}")
        return False

def main():
    """Run all preflight checks"""
    logger.info("Running preflight checks...")
    
    checks = [
        check_device_exists,
        check_gammu_config
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    
    if all_passed:
        logger.info("✓ All preflight checks passed")
        sys.exit(0)
    else:
        logger.error("❌ Some preflight checks failed")
        sys.exit(1)

if __name__ == '__main__':
    main() 