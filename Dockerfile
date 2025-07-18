FROM python:3.9-slim

# Install system dependencies for Playwright and timezone support
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    tzdata \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxss1 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxshmfence1 \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy gmail integration directory
COPY gmail_integration_temp /tmp/gmail_integration

# Install gmail integration
RUN pip install -e /tmp/gmail_integration

# Install Playwright browsers
RUN playwright install chromium

# Copy application files
COPY app.py .
COPY templates/ templates/

# Copy send-gmail utility (if it exists)
COPY send-gmail /usr/local/bin/send-gmail || true
RUN chmod +x /usr/local/bin/send-gmail || true

# Create directories with proper permissions
RUN mkdir -p /tmp /var/log /app/config && \
    chmod 755 /tmp /var/log /app/config

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]