"""
Database models
"""

import sqlite3
from datetime import datetime
import pytz
from .config import Config

def get_db():
    """Get database connection"""
    db = sqlite3.connect(Config.DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database with schema"""
    db = get_db()
    with open('database/schema.sql', 'r') as f:
        db.executescript(f.read())
    db.commit()
    db.close()

class User:
    @staticmethod
    def get_by_username(username):
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()
        return user

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
        db = get_db()
        try:
            db.execute('DELETE FROM users WHERE username = ?', (username,))
            db.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            db.close()

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
            cursor = db.execute('INSERT INTO messages (phone_number, content, sender_id) VALUES (?, ?, ?)',
                      (phone_number, content, sender_id))
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
            SELECT m.*, u.username as sender_name 
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
    def update_status(message_id, status):
        db = get_db()
        try:
            db.execute('''
                UPDATE messages 
                SET status = ?, sent_at = CASE WHEN ? = 'sent' THEN CURRENT_TIMESTAMP ELSE NULL END 
                WHERE id = ?
            ''', (status, status, message_id))
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