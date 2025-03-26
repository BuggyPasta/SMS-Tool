"""
Application configuration
""" 

import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Database configuration
    DATABASE = '/app/instance/database.db'
    
    # Device configuration
    USB_DEVICE = os.environ.get('USB_DEVICE', '/dev/ttyUSB3')
    GAMMU_CONFIG = os.environ.get('GAMMU_CONFIG', '/etc/gammurc')
    
    # Application settings
    MAX_SMS_LENGTH = 160
    DEFAULT_TEMPLATE = 'Default'
    TIMEZONE = 'Europe/London'
    
    # Admin settings
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')  # Default to 'admin' if not set
    
    # Application settings
    MAX_SMS_LENGTH = 160
    DEFAULT_TEMPLATE = 'Default'
    TIMEZONE = 'Europe/London' 