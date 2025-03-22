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

# Set proper permissions
chmod -R 777 /app/instance /app/logs
echo "Set directory permissions"

# Set proper permissions for USB device
if [ -e "/dev/ttyUSB3" ]; then
    chmod 666 /dev/ttyUSB3
    echo "Set permissions for /dev/ttyUSB3"
else
    echo "Warning: /dev/ttyUSB3 does not exist"
fi

# Run preflight checks
echo "Running preflight checks..."
python3 -c "from app.preflight import main; main()"
if [ $? -ne 0 ]; then
    echo "Preflight checks failed"
    exit 1
fi

# Initialize database if needed
echo "Initializing database..."
python3 -c "from app.models import init_db; init_db()" || {
    echo "Failed to initialize database through Python"
    echo "Attempting direct SQL initialization..."
    if [ -f "/app/database/schema.sql" ]; then
        sqlite3 /app/instance/database.db < /app/database/schema.sql && \
        echo "✓ Database initialized successfully" || \
        echo "Failed to initialize database"
    else
        echo "Schema file not found at /app/database/schema.sql"
        exit 1
    fi
}

# Debug information
echo "Current working directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Checking port 4001..."
netstat -tulpn | grep 4001 || echo "Port 4001 is free"
echo "Checking Gammu config..."
cat /etc/gammurc
echo "Checking file permissions..."
ls -la /etc/gammurc
echo
ls -la /app/instance
echo
ls -la /app/logs

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