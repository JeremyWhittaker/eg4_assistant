#!/bin/bash

# SSH commands to run on Solar Assistant server
HOST="172.16.106.13"
USER="solar-assistant"
PASS="solar123"

echo "Connecting to Solar Assistant server..."
echo ""

# Create a script with all commands
cat > /tmp/solar_commands.sh << 'EOF'
echo "=== 1. Finding Solar Assistant application directories ==="
sudo find /opt /var/www /home -name "solar_assistant*" -type d 2>/dev/null | head -10
echo ""

echo "=== 2. Looking for Phoenix/Elixir configuration files ==="
sudo find /opt -name "*.exs" -o -name "config.exs" 2>/dev/null | grep -i solar | head -20
echo ""

echo "=== 3. Checking for database configuration ==="
echo "PostgreSQL databases:"
sudo -u postgres psql -l 2>/dev/null | grep -i solar || echo "No PostgreSQL solar databases found"
echo ""
echo "SQLite/DB files:"
sudo find / -name "*.db" -o -name "*.sqlite*" 2>/dev/null | grep -i solar | head -10
echo ""

echo "=== 4. Finding inverter configuration ==="
echo "Searching for IP 172.16.107.129:"
sudo grep -r "172.16.107.129" /opt 2>/dev/null | head -10
echo ""
echo "Inverter config files:"
sudo find /etc /opt /var -name "*inverter*.conf" -o -name "*inverter*.json" 2>/dev/null | head -10
echo ""

echo "=== 5. Checking systemd service configuration ==="
sudo systemctl cat solar-assistant 2>/dev/null | head -50 || echo "solar-assistant service not found"
echo ""

echo "=== 6. Looking for configuration endpoints in Phoenix app ==="
sudo find /opt -name "*.ex" | xargs grep -l "configuration" 2>/dev/null | head -10
echo ""

echo "=== Additional checks ==="
echo "Checking /opt directory structure:"
sudo ls -la /opt/ | grep -i solar
echo ""
echo "Checking for web assets:"
sudo find /opt -name "index.html" -o -name "app.js" 2>/dev/null | grep -i solar | head -10
EOF

# Note to user about manual SSH
echo "Please run the following command manually to connect to Solar Assistant:"
echo "ssh solar-assistant@172.16.106.13"
echo "Password: solar123"
echo ""
echo "Then copy and paste these commands:"
echo ""
cat /tmp/solar_commands.sh