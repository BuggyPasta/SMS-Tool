"""
Flask application initialization
"""

from flask import Flask
from .config import Config
from .models import init_db
from .services import GammuService

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize database
    init_db()

    # Initialize Gammu service
    gammu_service = GammuService()

    # Register blueprints
    from .routes import auth_bp, admin_bp, user_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    return app 