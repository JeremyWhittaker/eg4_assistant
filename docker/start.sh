#!/bin/bash
# Solar Assistant Docker Startup Script

echo "Starting Solar Assistant..."

# Create necessary directories
mkdir -p /data/{db,logs,reports,backups,exports}
mkdir -p /app/config

# Check if config exists, if not copy default
if [ ! -f /app/config/config.yaml ]; then
    echo "Creating default configuration..."
    cp /app/config/config.yaml.default /app/config/config.yaml
fi

# Wait for dependent services
echo "Waiting for services to start..."
sleep 5

# Check MQTT connection
if [ "$MQTT_ENABLED" = "true" ]; then
    echo "Checking MQTT connection..."
    timeout 10 bash -c 'until echo > /dev/tcp/mqtt/1883; do sleep 1; done' 2>/dev/null && echo "MQTT is ready" || echo "MQTT connection failed"
fi

# Check InfluxDB connection
if [ "$INFLUXDB_ENABLED" = "true" ]; then
    echo "Checking InfluxDB connection..."
    timeout 10 bash -c 'until echo > /dev/tcp/influxdb/8086; do sleep 1; done' 2>/dev/null && echo "InfluxDB is ready" || echo "InfluxDB connection failed"
fi

# Start supervisor
echo "Starting supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf