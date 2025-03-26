"""
Database models
"""

import sqlite3
import os
from datetime import datetime
import pytz
from .config import Config
import logging
from .database import get_db, init_db  # Database utility functions

logger = logging.getLogger(__name__)

class User:
    @staticmethod
    def get_by_username(username):
        if username == 'admin':
            return {'id': 1, 'username': 'admin', 'is_admin': True}
        db = get_db()
        try:
            user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            return user
        except Exception as e:
            logger.error(f"Error getting user by username: {str(e)}")
            return None

    @staticmethod
    def get_by_id(user_id):
        if user_id == 1:  # Admin user
            return {'id': 1, 'username': 'admin', 'is_admin': True}
        db = get_db()
        try:
            user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
            return user
        except Exception as e:
            logger.error(f"Error getting user by id: {str(e)}")
            return None

    @staticmethod
    def authenticate(username, password):
        """Authenticate a user with username and password"""
        if username == 'admin':
            return {'id': 1, 'username': 'admin', 'is_admin': True} if password == Config.ADMIN_PASSWORD else None
        
        user = User.get_by_username(username)
        if user and user['password'] == password:  # In production, use proper password hashing
            return user
        return None

    @staticmethod
    def create(username, password, is_admin=False):
        if username == 'admin':  # Prevent creating another admin user
            return False
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                      (username, password, is_admin))
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return False

    @staticmethod
    def delete(username):
        if username == 'admin':  # Prevent deletion of admin user
            return False
        db = get_db()
        try:
            db.execute('DELETE FROM users WHERE username = ?', (username,))
            db.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False

    @staticmethod
    def update_password(username, new_password):
        if username == 'admin':  # Prevent changing admin password through the app
            return False
        db = get_db()
        try:
            db.execute('UPDATE users SET password = ? WHERE username = ?',
                      (new_password, username))
            db.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating password: {str(e)}")
            return False

    @staticmethod
    def get_all():
        """Get all users except admin"""
        db = get_db()
        try:
            users = db.execute('SELECT * FROM users WHERE username != "admin" ORDER BY username').fetchall()
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []

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

    @staticmethod
    def get_by_title(title):
        db = get_db()
        try:
            template = db.execute('SELECT * FROM templates WHERE title = ?', (title,)).fetchone()
            return template
        except Exception as e:
            logger.error(f"Error getting template by title: {str(e)}")
            return None

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

    @staticmethod
    def delete(title):
        if title == 'Default':
            return False
        db = get_db()
        try:
            db.execute('DELETE FROM templates WHERE title = ?', (title,))
            db.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting template: {str(e)}")
            return False

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

    @staticmethod
    def get_by_phone(phone_number, limit=25, offset=0):
        db = get_db()
        try:
            messages = db.execute('''
                SELECT m.*, u.username as sender_name 
                FROM messages m 
                JOIN users u ON m.sender_id = u.id 
                WHERE m.phone_number = ? 
                ORDER BY m.created_at DESC 
                LIMIT ? OFFSET ?
            ''', (phone_number, limit, offset)).fetchall()
            return messages
        except Exception as e:
            logger.error(f"Error getting messages by phone: {str(e)}")
            return []

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

    @staticmethod
    def delete(message_id):
        db = get_db()
        try:
            db.execute('DELETE FROM messages WHERE id = ?', (message_id,))
            db.commit()
            return True
        except sqlite3.Error:
            return False

    @staticmethod
    def delete_all():
        db = get_db()
        try:
            db.execute('DELETE FROM messages')
            db.commit()
            return True
        except sqlite3.Error:
            return False

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