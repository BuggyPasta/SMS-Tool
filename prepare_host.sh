#!/bin/bash
set -e

# Base directory for SMS tool data
BASE_DIR="/home/ovenking/docker_backup/sms_tool"

# Create necessary directories
mkdir -p "$BASE_DIR/database"
mkdir -p "$BASE_DIR/instance"
mkdir -p "$BASE_DIR/logs"

# Copy schema.sql to database directory
cp database/schema.sql "$BASE_DIR/database/"

# Set permissions (assuming gammuuser UID is 101 and dialout GID varies by system)
DIALOUT_GID=$(getent group dialout | cut -d: -f3)

# Set ownership and permissions
chown -R 101:$DIALOUT_GID "$BASE_DIR"
chmod -R 775 "$BASE_DIR"

echo "Host environment prepared successfully"
echo "Please ensure your user is in the dialout group:"
echo "sudo usermod -a -G dialout $USER"
echo "You may need to log out and back in for the group changes to take effect." 