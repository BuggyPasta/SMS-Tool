"""Database connection handling"""
import sqlite3
from flask import g, current_app
import os
import logging

logger = logging.getLogger(__name__)

def get_db():
    """Get database connection"""
    if 'db' not in g:
        try:
            g.db = sqlite3.connect(
                current_app.config['DATABASE'],
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
        except Exception as e:
            logger.error(f"Failed to establish database connection: {str(e)}")
            raise
    return g.db

def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")

def init_db():
    """Initialize the database"""
    try:
        # Get absolute path to schema file
        schema_path = os.path.join(current_app.root_path, '..', 'database', 'schema.sql')
        if not os.path.exists(schema_path):
            logger.error(f"Schema file not found at {schema_path}")
            return False

        # Ensure database directory exists
        db_dir = os.path.dirname(current_app.config['DATABASE'])
        os.makedirs(db_dir, exist_ok=True)

        # Get database connection
        db = get_db()
        
        # Read and execute schema
        with open(schema_path, 'r') as f:
            db.executescript(f.read())
        db.commit()
        
        # Verify database was initialized correctly
        try:
            # Check if templates table exists and has default template
            default_template = db.execute('SELECT * FROM templates WHERE title = ?', ('Default',)).fetchone()
            if not default_template:
                logger.error("Database initialization failed: default template not created")
                return False
                
            logger.info("Database initialization verified successfully")
            return True
        except Exception as e:
            logger.error(f"Database verification failed: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False

def init_app(app):
    """Initialize the database in the app context"""
    app.teardown_appcontext(close_db)
    try:
        with app.app_context():
            if not os.path.exists(app.config['DATABASE']):
                if not init_db():
                    logger.error("Failed to initialize database")
                    raise Exception("Database initialization failed")
    except Exception as e:
        logger.error(f"Failed to initialize app database: {str(e)}")
        raise 