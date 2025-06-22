FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY solar_assistant_web.py .
COPY simple_solar_web.py .
COPY real_data_collector.py .
COPY eg4_data_collector.py .
COPY eg4_custom_collector.py .
COPY luxpower_data_collector.py .
COPY modbus_data_collector.py .
COPY mqtt_bridge.py .
COPY data_collector.py .
COPY database.py .
COPY eg4_iotos_client.py .
COPY modbus_client.py .
COPY system_info.py .
COPY shared_data.py .
COPY config_watcher.py .

# Copy templates and static files
COPY templates /app/templates
COPY static /app/static

# Copy config directory
COPY config /app/config

# Create directories for persistent data
RUN mkdir -p /data/db /data/logs /data/config /data/exports

# Copy nginx config
COPY nginx.conf /etc/nginx/sites-available/default

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Expose ports
EXPOSE 80 5000 1883 8000

# Volume for persistent data
VOLUME ["/data"]

# Start supervisor
CMD ["/start.sh"]