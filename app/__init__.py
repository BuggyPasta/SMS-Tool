"""
Flask application initialization
"""

from flask import Flask, jsonify, render_template, g
from .config import Config
from .database import init_db, init_app as init_database
from .services.gammu_service import GammuService
from .logging_config import setup_logging
import atexit
import signal
import sys
import threading
import os

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

    # Ensure required directories exist
    os.makedirs(app.instance_path, exist_ok=True)
    logger.info("Ensured required directories exist")

    # Initialize database
    init_database(app)
    with app.app_context():
        init_db()
    logger.info("Database initialized successfully")

    # Initialize Gammu service
    global gammu_service
    gammu_service = GammuService()
    logger.info("Creating Gammu service instance")

    # Register cleanup function
    atexit.register(cleanup_gammu)
    logger.info("Registered cleanup functions")

    # Register blueprints
    from .routes import auth_bp, admin_bp, user_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/user')
    logger.info("Blueprints registered")

    # Register health check endpoint
    from .routes import register_health_check
    register_health_check(app)
    logger.info("Health check endpoint registered")

    @app.before_request
    def before_request():
        """Set up request context"""
        g.shutdown_event = shutdown_event
        g.gammu_service = gammu_service

    @app.teardown_appcontext
    def teardown_appcontext(exception=None):
        """Clean up request context"""
        if exception:
            logger.error(f"Error during request: {str(exception)}", exc_info=True)
        # Close any open database connections
        if hasattr(g, 'db'):
            try:
                g.db.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")

    @app.errorhandler(Exception)
    def handle_error(error):
        """Global error handler"""
        logger.error(f"Unhandled error: {str(error)}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': str(error) if app.debug else 'An unexpected error occurred'
        }), 500

    logger.info("App creation completed")
    return app 