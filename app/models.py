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
    return db

def init_db():
    """Initialize database with schema"""
    db = get_db()
    try:
        # Ensure database directory exists
        db_dir = os.path.dirname(Config.DATABASE)
        os.makedirs(db_dir, exist_ok=True)
        
        # Get schema path
        schema_path = os.path.join('/app', 'database', 'schema.sql')
        if not os.path.exists(schema_path):
            logger.error(f"Schema file not found at {schema_path}")
            raise FileNotFoundError(f"Schema file not found at {schema_path}")
        
        logger.info(f"Initializing database at {Config.DATABASE} with schema from {schema_path}")
        
        # Initialize database
        with open(schema_path, 'r') as f:
            db.executescript(f.read())
        db.commit()
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        db.close()

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
        db = get_db()
        templates = db.execute('SELECT * FROM templates ORDER BY title').fetchall()
        db.close()
        return templates

    @staticmethod
    def get_by_title(title):
        db = get_db()
        template = db.execute('SELECT * FROM templates WHERE title = ?', (title,)).fetchone()
        db.close()
        return template

    @staticmethod
    def create(title, content):
        db = get_db()
        try:
            db.execute('INSERT INTO templates (title, content) VALUES (?, ?)',
                      (title, content))
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            db.close()

    @staticmethod
    def update(title, content):
        db = get_db()
        try:
            db.execute('UPDATE templates SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE title = ?',
                      (content, title))
            db.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            db.close()

    @staticmethod
    def delete(title):
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
    def get_all(limit=25, offset=0):
        db = get_db()
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
        ''', (limit, offset)).fetchall()
        db.close()
        return messages

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