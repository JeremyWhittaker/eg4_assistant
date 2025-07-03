#!/bin/bash
# Script to update timezone and restart container

TIMEZONE=$1
CONTAINER_NAME="eg4-srp-monitor"

if [ -z "$TIMEZONE" ]; then
    echo "Usage: $0 <timezone>"
    echo "Example: $0 America/Phoenix"
    exit 1
fi

# Update docker-compose.yml with new timezone
sed -i "s/TZ=.*/TZ=$TIMEZONE/" docker-compose.yml

# Restart container
echo "Updating timezone to $TIMEZONE and restarting container..."
docker compose restart $CONTAINER_NAME

echo "Container restarted with timezone: $TIMEZONE"