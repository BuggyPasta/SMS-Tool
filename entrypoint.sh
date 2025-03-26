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

# Set Python path and Flask environment
export PYTHONPATH=/app:${PYTHONPATH:-}
export FLASK_APP=app
export FLASK_ENV=production
export FLASK_DEBUG=0

# Create directories
mkdir -p /app/instance /app/logs
echo "Created necessary directories"

# Set proper permissions
chmod -R 777 /app/instance /app/logs
echo "Set directory permissions"

# Set proper permissions for USB device
if [ -e "${USB_DEVICE}" ]; then
    chmod 666 "${USB_DEVICE}"
    echo "Set permissions for ${USB_DEVICE}"
else
    echo "Warning: ${USB_DEVICE} does not exist"
fi

# Run preflight checks
echo "Running preflight checks..."
python3 -c "from app.preflight import main; main()"
if [ $? -ne 0 ]; then
    echo "Preflight checks failed"
    exit 1
fi

# Initialize database
echo "Initializing database..."
if ! python3 -m app.init_db; then
    echo "Failed to initialize database"
    exit 1
fi
echo "✓ Database initialized successfully"

# Debug information
echo "Current working directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Flask environment:"
echo "FLASK_APP=$FLASK_APP"
echo "FLASK_ENV=$FLASK_ENV"
echo "FLASK_DEBUG=$FLASK_DEBUG"
echo "Checking port 4001..."
netstat -tulpn | grep 4001 || echo "Port 4001 is free"
echo "Checking Gammu config..."
cat /etc/gammurc
echo
echo "Checking file permissions..."
ls -la /etc/gammurc
echo
ls -la /app/instance
echo
ls -la /app/logs

# Start Flask application
echo "Starting Flask application..."
cd /app  # Ensure we're in the right directory
exec python3 -m flask run --host=0.0.0.0 --port=4001 