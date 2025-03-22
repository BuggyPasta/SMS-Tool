#!/bin/bash
set -e

# Base directory for SMS tool data
BASE_DIR="/home/ovenking/docker_backup/sms_tool"

# Create necessary directories
for dir in "$BASE_DIR/database" "$BASE_DIR/instance" "$BASE_DIR/logs"; do
    mkdir -p "$dir"
    echo "Created directory: $dir"
done

# Get current script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Copy schema.sql to database directory
SCHEMA_SRC="$SCRIPT_DIR/database/schema.sql"
SCHEMA_DEST="$BASE_DIR/database/schema.sql"

if [ ! -f "$SCHEMA_SRC" ]; then
    echo "Error: Schema file not found at $SCHEMA_SRC"
    exit 1
fi

echo "Copying schema.sql..."
cp "$SCHEMA_SRC" "$SCHEMA_DEST"
echo "✓ Copied schema.sql"

echo "Directory contents:"
ls -la "$BASE_DIR"
ls -la "$BASE_DIR/database"
ls -la "$BASE_DIR/logs"
ls -la "$BASE_DIR/instance"

echo
echo "✓ Host environment prepared successfully" 