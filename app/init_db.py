"""Database initialization script"""
from app import create_app
from app.database import init_db, get_db
import logging

logger = logging.getLogger(__name__)

def main():
    """Initialize the database"""
    try:
        app = create_app()
        with app.app_context():
            if not init_db():
                logger.error("Database initialization failed")
                return False
                
            # Verify database connection
            db = get_db()
            if not db.is_connected():
                logger.error("Database connection verification failed")
                return False
                
            logger.info("Database initialized successfully")
            return True
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False

if __name__ == '__main__':
    import sys
    sys.exit(0 if main() else 1) 