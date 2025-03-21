"""
Centralized logging configuration for the SMS Tool application
"""

import logging
import logging.handlers
import os
from typing import Dict, Optional
import uuid
from flask import request, has_request_context

class RequestIdFilter(logging.Filter):
    """Adds request ID to log records"""
    def filter(self, record):
        if has_request_context():
            record.request_id = getattr(request, 'id', 'no-request-id')
        else:
            record.request_id = 'no-request-id'
        return True

def get_log_level() -> int:
    """Get log level from environment or default to INFO"""
    level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
    return getattr(logging.getLevelName(level_name), 'INFO')

def create_rotating_handler(filename: str, max_bytes: int = 10485760, backup_count: int = 5) -> logging.Handler:
    """Create a rotating file handler with the specified parameters"""
    handler = logging.handlers.RotatingFileHandler(
        filename=filename,
        maxBytes=max_bytes,  # 10MB
        backupCount=backup_count
    )
    return handler

def remove_existing_handlers(logger: logging.Logger) -> None:
    """Remove any existing handlers from a logger"""
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

def create_formatter(include_process: bool = False) -> logging.Formatter:
    """Create a formatter with the specified format"""
    format_parts = ['%(asctime)s - %(request_id)s - %(name)s - %(levelname)s']
    if include_process:
        format_parts.append('- PID:%(process)d')
    format_parts.extend(['- %(message)s'])
    
    return logging.Formatter(' '.join(format_parts))

def setup_logger(name: str, log_file: Optional[str] = None, level: Optional[int] = None) -> logging.Logger:
    """Setup a logger with the specified configuration"""
    logger = logging.getLogger(name)
    remove_existing_handlers(logger)
    
    # Set level
    logger.setLevel(level or get_log_level())
    
    # Add request ID filter
    logger.addFilter(RequestIdFilter())
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(create_formatter())
    logger.addHandler(console_handler)
    
    # Create file handler if log file specified
    if log_file:
        file_handler = create_rotating_handler(log_file)
        file_handler.setFormatter(create_formatter(include_process=True))
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def setup_logging() -> Dict[str, logging.Logger]:
    """Configure logging for all application components"""
    # Ensure log directory exists
    os.makedirs('/app/logs', exist_ok=True)
    
    # Get base log level
    base_level = get_log_level()
    
    # Configure root logger
    root_logger = logging.getLogger()
    remove_existing_handlers(root_logger)
    root_logger.setLevel(base_level)
    
    # Setup component loggers
    loggers = {
        'app': setup_logger('app', '/app/logs/app.log', base_level),
        'gammu': setup_logger('gammu', '/app/logs/gammu.log', base_level),
        'models': setup_logger('models', '/app/logs/models.log', base_level),
        'routes': setup_logger('routes', '/app/logs/routes.log', base_level)
    }
    
    # Log startup information
    for name, logger in loggers.items():
        logger.info(f"Logger '{name}' initialized with level {logging.getLevelName(logger.level)}")
    
    return loggers

def get_request_id() -> str:
    """Generate or get request ID"""
    if has_request_context():
        if not hasattr(request, 'id'):
            request.id = str(uuid.uuid4())
        return request.id
    return 'no-request-id' 