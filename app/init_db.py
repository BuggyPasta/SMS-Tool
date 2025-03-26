"""Database initialization script"""
import os
import sys
from app import create_app
from app.database import get_db, init_db
import logging

logger = logging.getLogger('init_db')

def main():
    """Main function to initialize the database"""
    try:
        app = create_app()
        with app.app_context():
            # Check database connection
            try:
                db = get_db()
                # Test connection with a simple query
                db.execute('SELECT 1').fetchone()
            except Exception as e:
                logger.error(f"Database connection failed: {str(e)}")
                sys.exit(1)
                
            # Initialize database
            if not init_db():
                logger.error("Database initialization failed")
                sys.exit(1)
                
            logger.info("Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 