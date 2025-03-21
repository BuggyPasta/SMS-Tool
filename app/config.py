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
    DATABASE = '/app/database/sms.db'
    
    # Gammu configuration
    GAMMU_CONFIG = '/root/gammurc'
    
    # Application settings
    MAX_SMS_LENGTH = 160
    DEFAULT_TEMPLATE = 'Default'
    TIMEZONE = 'Europe/London' 