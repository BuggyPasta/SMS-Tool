import sqlite3
from flask import g, current_app
import os

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with current_app.open_resource('database/schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

def is_connected():
    try:
        db = get_db()
        db.execute('SELECT 1').fetchone()
        return True
    except sqlite3.Error:
        return False

def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        if not os.path.exists(app.config['DATABASE']):
            init_db() 