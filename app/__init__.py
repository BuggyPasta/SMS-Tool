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
    """Cleanup function to properly close Gammu connection"""
    global gammu_service
    if gammu_service:
        try:
            gammu_service.close()
            logger.info("Gammu service cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during Gammu cleanup: {e}")

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

    try:
        # Initialize Gammu service
        global gammu_service
        gammu_service = GammuService()
        logger.info("Gammu service initialized successfully")
        
        # Register cleanup functions
        atexit.register(cleanup_gammu)
    except Exception as e:
        logger.error(f"Failed to initialize Gammu service: {str(e)}")
        raise

    # Register blueprints
    from .routes import auth_bp, admin_bp, user_bp, register_health_check
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    
    # Register health check endpoint
    register_health_check(app)

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

    return app 