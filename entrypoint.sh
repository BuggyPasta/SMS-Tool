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

# Set Python path
export PYTHONPATH=/app:${PYTHONPATH:-}

# Create directories
mkdir -p /app/instance /app/logs
echo "Created necessary directories"

# Run preflight checks
echo "Running preflight checks..."
python3 -c "from app.preflight import main; main()"
if [ $? -ne 0 ]; then
    echo "Preflight checks failed"
    exit 1
fi

# Initialize database if needed
if [ ! -f "/app/instance/database.db" ]; then
    echo "Initializing database..."
    sqlite3 /app/instance/database.db < /app/database/schema.sql
    echo "✓ Database initialized successfully"
fi

# Debug information
echo "Current working directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Checking port 4001..."
netstat -tulpn | grep 4001 || echo "Port 4001 is free"
echo "Checking Gammu config..."
cat /etc/gammurc
echo "Checking file permissions..."
ls -la /app/instance /app/logs /etc/gammurc

# Start Flask application
echo "Starting Flask application..."
cd /app

# Start gunicorn with debug output
PYTHONUNBUFFERED=1 FLASK_DEBUG=1 exec gunicorn \
    --bind 0.0.0.0:4001 \
    --workers 1 \
    --timeout 120 \
    --pid /app/flask.pid \
    --log-level debug \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    --capture-output \
    --enable-stdio-inheritance \
    --preload \
    'app:create_app()' 