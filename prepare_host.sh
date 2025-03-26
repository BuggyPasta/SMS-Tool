#!/bin/bash
set -e

# This script requires the .env file to be sourced before running
# Example: source .env && ./prepare_host.sh
# or: export BASE_PATH=/your/path && ./prepare_host.sh

# Check if BASE_PATH environment variable is set
if [ -z "$BASE_PATH" ]; then
    echo "Error: BASE_PATH environment variable is not set"
    echo "Please set it in your .env file"
    echo "Example: BASE_PATH=/home/YOUR_USER_FOLDER/sms-tool"
    exit 1
fi

# Create necessary directories
for dir in "$BASE_PATH/database" "$BASE_PATH/instance" "$BASE_PATH/logs"; do
    mkdir -p "$dir"
    echo "Created directory: $dir"
done

# Create Gammu config file
GAMMU_CONFIG="$BASE_PATH/gammurc"
if [ ! -f "$GAMMU_CONFIG" ]; then
    echo "Creating Gammu config file..."
    cat > "$GAMMU_CONFIG" << 'EOL'
[gammu]
device = /dev/ttyUSB3
connection = at19200
logfile = /app/logs/gammu.log
loglevel = debug
EOL
    chmod 644 "$GAMMU_CONFIG"
    echo "✓ Created Gammu config file"
fi

# Get current script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Copy schema.sql to database directory
SCHEMA_SRC="$SCRIPT_DIR/database/schema.sql"
SCHEMA_DEST="$BASE_PATH/database/schema.sql"

if [ ! -f "$SCHEMA_SRC" ]; then
    echo "Error: Schema file not found at $SCHEMA_SRC"
    exit 1
fi

echo "Copying schema.sql..."
cp "$SCHEMA_SRC" "$SCHEMA_DEST"
echo "✓ Copied schema.sql"

echo "Directory contents:"
ls -la "$BASE_PATH"
ls -la "$BASE_PATH/database"
ls -la "$BASE_PATH/logs"
ls -la "$BASE_PATH/instance"

echo
echo "✓ Host environment prepared successfully" 