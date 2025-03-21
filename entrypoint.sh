#!/bin/bash
set -e

# Function to handle shutdown
cleanup() {
    echo "Received shutdown signal"
    # Kill the Flask process if it exists
    if [ -f /app/flask.pid ]; then
        kill -TERM $(cat /app/flask.pid) 2>/dev/null || true
    fi
    exit 0
}

# Set up signal traps
trap cleanup SIGTERM SIGINT

# Run preflight checks
echo "Running preflight checks..."
python3 /app/preflight.py

# Initialize database if needed
if [ ! -f "/app/database/database.db" ]; then
    echo "Initializing database with schema from /app/database/schema.sql"
    sqlite3 /app/database/database.db < /app/database/schema.sql
    echo "Database initialized successfully"
fi

# Create log directory with proper permissions
mkdir -p /app/logs
chown -R gammuuser:dialout /app/logs

# Start Flask application
echo "Starting Flask application..."
cd /app
exec gunicorn --bind 0.0.0.0:4001 \
    --workers 1 \
    --timeout 120 \
    --pid /app/flask.pid \
    --log-level info \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    'app:create_app()' 