#!/usr/bin/env python3
"""
Preflight checks for SMS Tool
"""

import os
import sys
import gammu
import logging
from .config import Config
from .logging_config import setup_logging

# Set up logging
loggers = setup_logging()
logger = loggers['app']

def check_device_exists():
    """Check if the USB device exists and is accessible"""
    device_path = Config.USB_DEVICE
    if not os.path.exists(device_path):
        logger.error(f"❌ Device {device_path} does not exist")
        return False
    
    # Check device permissions
    try:
        mode = os.stat(device_path).st_mode
        if not mode & os.W_OK:
            logger.error(f"❌ Device {device_path} is not writable")
            return False
        if not mode & os.R_OK:
            logger.error(f"❌ Device {device_path} is not readable")
            return False
    except OSError as e:
        logger.error(f"❌ Cannot access device {device_path}: {e}")
        return False
        
    logger.info(f"✓ Device {device_path} exists and is accessible")
    return True

def check_gammu_config():
    """Check if Gammu config is readable and valid"""
    config_path = Config.GAMMU_CONFIG
    try:
        if not os.path.exists(config_path):
            logger.error(f"❌ Gammu config file {config_path} does not exist")
            return False
            
        # Check config file permissions
        if not os.access(config_path, os.R_OK):
            logger.error(f"❌ Gammu config file {config_path} is not readable")
            return False
        
        # Try to read config without initializing
        sm = gammu.StateMachine()
        sm.ReadConfig(Filename=config_path)
        logger.info("✓ Gammu config is valid")
        return True
    except Exception as e:
        logger.error(f"❌ Error checking Gammu config: {e}")
        return False

def check_instance_dir():
    """Check if instance directory exists and is writable"""
    instance_dir = os.path.dirname(Config.DATABASE)
    try:
        os.makedirs(instance_dir, exist_ok=True)
        test_file = os.path.join(instance_dir, 'test_write')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info(f"✓ Instance directory {instance_dir} is writable")
        return True
    except Exception as e:
        logger.error(f"❌ Cannot write to instance directory {instance_dir}: {e}")
        return False

def main():
    """Run all preflight checks"""
    logger.info("Running preflight checks...")
    
    checks = [
        check_device_exists,
        check_gammu_config,
        check_instance_dir
    ]
    
    all_passed = True
    for check in checks:
        try:
            if not check():
                all_passed = False
        except Exception as e:
            logger.error(f"Check failed with error: {e}")
            all_passed = False
    
    if all_passed:
        logger.info("✓ All preflight checks passed")
        sys.exit(0)
    else:
        logger.error("❌ Some preflight checks failed")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Preflight checks failed with error: {e}")
        sys.exit(1) 