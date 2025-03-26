"""
Centralized logging configuration for the SMS Tool application
"""

import logging
import logging.handlers
import os
import sys
from typing import Dict, Optional
import uuid
from flask import request, has_request_context
from pathlib import Path
from werkzeug.local import LocalProxy

# Constants
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s' if has_request_context() else '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_DIR = Path('/app/logs')
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

class RequestIdFilter(logging.Filter):
    """Add request_id to log records if available."""
    def filter(self, record):
        if not hasattr(record, 'request_id'):
            record.request_id = get_request_id() if has_request_context() else 'no_request'
        return True

def get_request_id() -> str:
    """Get current request ID or generate a new one."""
    if not hasattr(request, 'id'):
        setattr(request, 'id', str(uuid.uuid4()))
    return getattr(request, 'id')

def get_log_level() -> int:
    """Get log level from environment or default to INFO"""
    level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
    try:
        return logging._nameToLevel[level_name]
    except KeyError:
        return DEFAULT_LOG_LEVEL

def ensure_log_directory() -> bool:
    """Ensure log directory exists and is writable."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        # Test write permissions
        test_file = LOG_DIR / '.test_write'
        test_file.touch()
        test_file.unlink()
        return True
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not create/write to log directory: {e}", file=sys.stderr)
        return False

def create_formatter() -> logging.Formatter:
    """Create log formatter with request ID."""
    return logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)

def create_console_handler() -> logging.Handler:
    """Create console handler with proper formatting."""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(create_formatter())
    return console_handler

def create_file_handler(filename: str) -> Optional[logging.Handler]:
    """Create rotating file handler with error handling."""
    if not ensure_log_directory():
        return None
        
    try:
        file_path = LOG_DIR / filename
        handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        handler.setFormatter(create_formatter())
        return handler
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not create log file handler for {filename}: {e}", file=sys.stderr)
        return None

def setup_component_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Set up logger for a specific component with fallback handling."""
    logger = logging.getLogger(name)
    logger.setLevel(level or get_log_level())
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Always add console handler
    console_handler = create_console_handler()
    logger.addHandler(console_handler)
    
    # Try to add file handler
    file_handler = create_file_handler(f"{name}.log")
    if file_handler:
        logger.addHandler(file_handler)
    
    # Add request ID filter
    logger.addFilter(RequestIdFilter())
    
    return logger

def setup_logging() -> Dict[str, logging.Logger]:
    """Initialize all application loggers with error handling."""
    try:
        # Set up component loggers
        loggers = {
            'app': setup_component_logger('app'),
            'gammu': setup_component_logger('gammu'),
            'routes': setup_component_logger('routes'),
            'models': setup_component_logger('models')
        }
        
        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(get_log_level())
        
        return loggers
    except Exception as e:
        # Ensure we have at least console logging in case of setup failure
        print(f"Critical: Failed to set up logging: {e}", file=sys.stderr)
        fallback_logger = logging.getLogger()
        fallback_logger.setLevel(DEFAULT_LOG_LEVEL)
        fallback_logger.addHandler(create_console_handler())
        return {'app': fallback_logger} 