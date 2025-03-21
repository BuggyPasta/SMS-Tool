"""
Flask application initialization
"""

from flask import Flask, jsonify, render_template
from .config import Config
from .models import init_db
from .services import GammuService
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/app.log')
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure log directory exists
    os.makedirs('/app/logs', exist_ok=True)

    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

    try:
        # Initialize Gammu service
        gammu_service = GammuService()
        logger.info("Gammu service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gammu service: {str(e)}")
        raise

    # Register blueprints
    from .routes import auth_bp, admin_bp, user_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)

    # Register health check route
    @app.route('/health')
    def health_check():
        try:
            # Check database connection
            from .models import User
            User.get_all()
            # Check Gammu connection
            gammu_service.connect()
            return jsonify({'status': 'healthy'}), 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    return app 