"""
Flask application initialization
"""

from flask import Flask, jsonify, render_template, g
from .config import Config
from .models import init_db
from .services.gammu_service import GammuService
from .logging_config import setup_logging
import atexit
import signal
import sys
import threading

# Setup logging
loggers = setup_logging()
logger = loggers['app']

# Global Gammu service instance
gammu_service = None

# Shutdown event for graceful termination
shutdown_event = threading.Event()

def signal_handler(signum, frame):
    """Handle termination signals"""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received signal {signal_name}")
    shutdown_event.set()
    cleanup_gammu()
    sys.exit(0)

def cleanup_gammu():
    """Clean up Gammu service"""
    global gammu_service
    if gammu_service and gammu_service.is_connected():
        logger.info("Cleaning up Gammu service")
        try:
            gammu_service.disconnect()
            logger.info("Successfully disconnected Gammu service")
        except Exception as e:
            logger.error(f"Error during Gammu cleanup: {e}")

def create_app():
    """Create and configure the Flask application"""
    logger.info("Starting app creation")
    app = Flask(__name__)
    app.config.from_object(Config)
    logger.info("Loaded configuration")

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logger.info("Registered signal handlers")

    try:
        # Initialize database
        logger.info("Initializing database")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

    try:
        # Initialize Gammu service (but don't connect yet)
        logger.info("Creating Gammu service instance")
        global gammu_service
        gammu_service = GammuService()
        
        # Register cleanup functions
        atexit.register(cleanup_gammu)
        logger.info("Registered cleanup functions")
    except Exception as e:
        logger.error(f"Failed to create Gammu service: {str(e)}")
        raise

    # Register blueprints
    logger.info("Registering blueprints")
    from .routes import auth_bp, admin_bp, user_bp, register_health_check
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    logger.info("Blueprints registered")
    
    # Register health check endpoint
    logger.info("Registering health check endpoint")
    register_health_check(app)
    logger.info("Health check endpoint registered")

    @app.before_request
    def before_request():
        """Set up request context"""
        g.shutdown_event = shutdown_event

    @app.teardown_appcontext
    def teardown_appcontext(exception=None):
        """Clean up request context"""
        if exception:
            logger.error(f"Error during request: {str(exception)}")

    @app.errorhandler(Exception)
    def handle_error(error):
        """Global error handler"""
        logger.error(f"Unhandled error: {str(error)}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': str(error)
        }), 500

    logger.info("App creation completed")
    return app 