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

# Function to check directory permissions
check_directory() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        echo "Error: Directory $dir does not exist"
        return 1
    fi
    if [ ! -w "$dir" ]; then
        echo "Error: Directory $dir is not writable"
        return 1
    fi
    return 0
}

# Verify directories and permissions
echo "Verifying directories and permissions..."
for dir in /app/instance /app/logs; do
    if ! check_directory "$dir"; then
        echo "Error: Directory $dir is not accessible"
        exit 1
    fi
done

# Verify schema file exists
if [ ! -f "/app/database/schema.sql" ]; then
    echo "Error: Schema file not found"
    exit 1
fi

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