#!/bin/bash
set -e

# Base directory for SMS tool data
BASE_DIR="/home/ovenking/docker_backup/sms_tool"
GAMMU_UID=101

# Get dialout group ID
if ! DIALOUT_GID=$(getent group dialout | cut -d: -f3); then
    echo "Error: dialout group not found"
    exit 1
fi

echo "Using UID=$GAMMU_UID (gammuuser) and GID=$DIALOUT_GID (dialout)"

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

# Set ownership and permissions
echo "Setting ownership and permissions..."

# Set directory permissions
find "$BASE_DIR" -type d -exec chmod 775 {} \;
find "$BASE_DIR" -type f -exec chmod 664 {} \;

# Set ownership
chown -R $GAMMU_UID:$DIALOUT_GID "$BASE_DIR"

# Verify setup
echo "Verifying setup..."

# Check schema file
if [ ! -f "$SCHEMA_DEST" ]; then
    echo "❌ Schema file not found at destination"
    exit 1
fi
echo "✓ Schema file exists"

# Check permissions
if [ ! -r "$SCHEMA_DEST" ]; then
    echo "❌ Schema file not readable"
    exit 1
fi
echo "✓ Schema file is readable"

# Check directory permissions
for dir in "$BASE_DIR/database" "$BASE_DIR/instance" "$BASE_DIR/logs"; do
    if [ ! -w "$dir" ]; then
        echo "❌ Directory not writable: $dir"
        exit 1
    fi
    echo "✓ Directory is writable: $dir"
done

echo "Directory permissions:"
ls -la "$BASE_DIR"
ls -la "$BASE_DIR/database"
ls -la "$BASE_DIR/logs"
ls -la "$BASE_DIR/instance"

echo
echo "✓ Host environment prepared successfully"
echo
echo "Please ensure your user is in the dialout group:"
echo "sudo usermod -a -G dialout $USER"
echo "You may need to log out and back in for the group changes to take effect." 