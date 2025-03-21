#!/usr/bin/env python3
"""
Preflight checks for SMS Tool
"""

import os
import sys
import grp
import pwd
import gammu
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_device_exists():
    """Check if the USB device exists"""
    if not os.path.exists('/dev/ttyUSB3'):
        logger.error("❌ Device /dev/ttyUSB3 does not exist")
        return False
    logger.info("✓ Device exists")
    return True

def check_device_permissions():
    """Check device permissions"""
    try:
        stat = os.stat('/dev/ttyUSB3')
        mode = stat.st_mode
        if not (mode & 0o660):
            logger.error("❌ Device does not have correct permissions (needs 660)")
            return False
        logger.info("✓ Device has correct permissions")
        return True
    except Exception as e:
        logger.error(f"❌ Error checking device permissions: {e}")
        return False

def check_user_groups():
    """Check if current user is in dialout group"""
    try:
        # Get dialout group info
        dialout_gid = grp.getgrnam('dialout').gr_gid
        
        # Check primary group
        primary_gid = os.getgid()
        if primary_gid == dialout_gid:
            logger.info("✓ User's primary group is dialout")
            return True
            
        # Check supplementary groups
        groups = os.getgroups()
        logger.info(f"User groups: primary={primary_gid}, supplementary={groups}")
        
        if dialout_gid in groups:
            logger.info("✓ User has dialout as supplementary group")
            return True
            
        logger.error(f"❌ Current user is not in dialout group (gid={dialout_gid})")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking user groups: {e}")
        return False

def check_gammu_config():
    """Check if Gammu config is readable and valid"""
    try:
        if not os.path.exists('/etc/gammurc'):
            logger.error("❌ Gammu config file does not exist")
            return False
        
        # Try to read config
        sm = gammu.StateMachine()
        sm.ReadConfig(Filename='/etc/gammurc')
        logger.info("✓ Gammu config is valid")
        return True
    except Exception as e:
        logger.error(f"❌ Error checking Gammu config: {e}")
        return False

def check_device_busy():
    """Check if device is already in use"""
    try:
        import fcntl
        import termios
        fd = os.open('/dev/ttyUSB3', os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.close(fd)
        logger.info("✓ Device is not busy")
        return True
    except IOError:
        logger.error("❌ Device is busy or locked by another process")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking device busy status: {e}")
        return False

def main():
    """Run all preflight checks"""
    logger.info("Running preflight checks...")
    
    checks = [
        check_device_exists,
        check_device_permissions,
        check_user_groups,
        check_gammu_config,
        check_device_busy
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