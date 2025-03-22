"""
Database models
"""

import sqlite3
import os
from datetime import datetime
import pytz
from .config import Config
import logging

logger = logging.getLogger(__name__)

def get_db():
    """Get database connection"""
    db = sqlite3.connect(Config.DATABASE)
    db.row_factory = sqlite3.Row
    
    # Add connection check method
    def is_connected():
        try:
            db.execute('SELECT 1').fetchone()
            return True
        except sqlite3.Error:
            return False
    
    # Attach the method to the connection object
    db.is_connected = is_connected
    return db

def init_db():
    """Initialize the database"""
    db = None
    try:
        # Get absolute path to schema file
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'schema.sql')
        if not os.path.exists(schema_path):
            logger.error(f"Schema file not found at {schema_path}")
            return False

        logger.info(f"Initializing database with schema from {schema_path}")
        
        # Ensure database directory exists
        db_dir = os.path.dirname(Config.DATABASE)
        os.makedirs(db_dir, exist_ok=True)
        
        # Get database connection
        db = get_db()
        
        # Read and execute schema
        with open(schema_path, 'r') as f:
            db.executescript(f.read())
        db.commit()
        
        # Verify database was initialized correctly
        try:
            # Check if users table exists and has admin user
            admin = db.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
            if not admin:
                logger.error("Database initialization failed: admin user not created")
                return False
                
            # Check if templates table exists and has default template
            default_template = db.execute('SELECT * FROM templates WHERE title = ?', ('Default',)).fetchone()
            if not default_template:
                logger.error("Database initialization failed: default template not created")
                return False
                
            logger.info("Database initialization verified successfully")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database verification failed: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")

class User:
    @staticmethod
    def get_by_username(username):
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()
        return user

    @staticmethod
    def get_by_id(user_id):
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        db.close()
        return user

    @staticmethod
    def authenticate(username, password):
        """Authenticate a user with username and password"""
        user = User.get_by_username(username)
        if user and user['password'] == password:  # In production, use proper password hashing
            return user
        return None

    @staticmethod
    def create(username, password, is_admin=False):
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                      (username, password, is_admin))
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            db.close()

    @staticmethod
    def delete(username):
        if username == 'admin':  # Prevent deletion of admin user
            return False
        db = get_db()
        try:
            db.execute('DELETE FROM users WHERE username = ?', (username,))
            db.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            db.close()

    @staticmethod
    def update_password(username, new_password):
        db = get_db()
        try:
            db.execute('UPDATE users SET password = ? WHERE username = ?',
                      (new_password, username))
            db.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            db.close()

    @staticmethod
    def get_all():
        """Get all users"""
        db = get_db()
        users = db.execute('SELECT * FROM users ORDER BY username').fetchall()
        db.close()
        return users

class Template:
    @staticmethod
    def get_all():
        """Get all templates, ensuring only one Default template exists"""
        db = get_db()
        try:
            # First, ensure only one Default template exists
            default_templates = db.execute('SELECT COUNT(*) as count FROM templates WHERE title = "Default"').fetchone()['count']
            if default_templates > 1:
                # Keep the most recently updated Default template
                db.execute('''
                    DELETE FROM templates 
                    WHERE title = "Default" 
                    AND id NOT IN (
                        SELECT id FROM templates 
                        WHERE title = "Default" 
                        ORDER BY COALESCE(updated_at, created_at) DESC 
                        LIMIT 1
                    )
                ''')
                db.commit()
            
            templates = db.execute('SELECT * FROM templates ORDER BY title').fetchall()
            return templates
        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}")
            return []
        finally:
            if db:
                try:
                    db.close()
                except Exception as e:
                    logger.error(f"Error closing database connection: {str(e)}")

    @staticmethod
    def get_by_title(title):
        db = get_db()
        template = db.execute('SELECT * FROM templates WHERE title = ?', (title,)).fetchone()
        db.close()
        return template

    @staticmethod
    def create(title, content):
        """Create a new template, preventing duplicate titles"""
        db = get_db()
        try:
            # Check if template with this title already exists
            existing = db.execute('SELECT COUNT(*) as count FROM templates WHERE title = ?', (title,)).fetchone()['count']
            if existing > 0:
                return False
            
            now = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
            db.execute('''
                INSERT INTO templates (title, content, created_at, updated_at) 
                VALUES (?, ?, ?, ?)
            ''', (title, content, now, now))
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            return False
        finally:
            if db:
                try:
                    db.close()
                except Exception as e:
                    logger.error(f"Error closing database connection: {str(e)}")

    @staticmethod
    def update(title, content):
        db = get_db()
        try:
            now = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
            db.execute('''
                UPDATE templates 
                SET content = ?, updated_at = ? 
                WHERE title = ?
            ''', (content, now, title))
            db.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating template: {str(e)}")
            return False
        finally:
            if db:
                try:
                    db.close()
                except Exception as e:
                    logger.error(f"Error closing database connection: {str(e)}")

    @staticmethod
    def delete(title):
        if title == 'Default':
            return False
        db = get_db()
        try:
            db.execute('DELETE FROM templates WHERE title = ?', (title,))
            db.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            db.close()

class Message:
    @staticmethod
    def create(phone_number, content, sender_id):
        db = get_db()
        try:
            cursor = db.execute('''
                INSERT INTO messages (phone_number, content, sender_id, status, queued_at) 
                VALUES (?, ?, ?, 'queued', CURRENT_TIMESTAMP)
            ''', (phone_number, content, sender_id))
            db.commit()
            return cursor.lastrowid
        except sqlite3.Error:
            return None
        finally:
            db.close()

    @staticmethod
    def get_all(page=1, per_page=25, phone_filter=None):
        """Get all messages with pagination and optional phone filter"""
        db = get_db()
        offset = (page - 1) * per_page
        try:
            if phone_filter:
                messages = db.execute('''
                    SELECT m.*, u.username as sender_name,
                           CASE 
                               WHEN m.status = 'queued' THEN m.queued_at
                               WHEN m.status = 'sending' THEN m.sending_at
                               WHEN m.status = 'sent' THEN m.sent_at
                               WHEN m.status = 'delivered' THEN m.delivered_at
                               WHEN m.status = 'failed' THEN m.failed_at
                               ELSE m.created_at
                           END as status_time
                    FROM messages m 
                    JOIN users u ON m.sender_id = u.id 
                    WHERE m.phone_number = ?
                    ORDER BY m.created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (phone_filter, per_page, offset)).fetchall()
            else:
                messages = db.execute('''
                    SELECT m.*, u.username as sender_name,
                           CASE 
                               WHEN m.status = 'queued' THEN m.queued_at
                               WHEN m.status = 'sending' THEN m.sending_at
                               WHEN m.status = 'sent' THEN m.sent_at
                               WHEN m.status = 'delivered' THEN m.delivered_at
                               WHEN m.status = 'failed' THEN m.failed_at
                               ELSE m.created_at
                           END as status_time
                    FROM messages m 
                    JOIN users u ON m.sender_id = u.id 
                    ORDER BY m.created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (per_page, offset)).fetchall()
            return messages
        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}")
            return []
        finally:
            db.close()

    @staticmethod
    def get_by_phone(phone_number, limit=25, offset=0):
        db = get_db()
        messages = db.execute('''
            SELECT m.*, u.username as sender_name 
            FROM messages m 
            JOIN users u ON m.sender_id = u.id 
            WHERE m.phone_number = ? 
            ORDER BY m.created_at DESC 
            LIMIT ? OFFSET ?
        ''', (phone_number, limit, offset)).fetchall()
        db.close()
        return messages

    @staticmethod
    def update_status(message_id, status, error_message=None):
        db = get_db()
        try:
            timestamp_field = {
                'queued': 'queued_at',
                'sending': 'sending_at',
                'sent': 'sent_at',
                'delivered': 'delivered_at',
                'failed': 'failed_at'
            }.get(status)
            
            if timestamp_field:
                db.execute(f'''
                    UPDATE messages 
                    SET status = ?, {timestamp_field} = CURRENT_TIMESTAMP,
                        error_message = ?
                    WHERE id = ?
                ''', (status, error_message, message_id))
            else:
                db.execute('''
                    UPDATE messages 
                    SET status = ?, error_message = ?
                    WHERE id = ?
                ''', (status, error_message, message_id))
            
            db.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            db.close()

    @staticmethod
    def delete(message_id):
        db = get_db()
        try:
            db.execute('DELETE FROM messages WHERE id = ?', (message_id,))
            db.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            db.close()

    @staticmethod
    def delete_all():
        db = get_db()
        try:
            db.execute('DELETE FROM messages')
            db.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            db.close()

    @classmethod
    def get_total_pages(cls, per_page, phone_filter=None):
        """Get total number of pages for pagination"""
        db = get_db()
        try:
            if phone_filter:
                count = db.execute(
                    'SELECT COUNT(*) as total FROM messages WHERE phone_number = ?',
                    (phone_filter,)
                ).fetchone()['total']
            else:
                count = db.execute('SELECT COUNT(*) as total FROM messages').fetchone()['total']
            
            return (count + per_page - 1) // per_page  # Ceiling division
        except Exception as e:
            logger.error(f"Error getting total pages: {str(e)}")
            return 1  # Return at least 1 page on error 