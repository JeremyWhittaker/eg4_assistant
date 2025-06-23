#!/bin/bash
# Script to analyze Solar Assistant structure via SSH

SSH_HOST="solar-assistant@172.16.109.214"
SSH_PASS="solar123"

echo "=== Analyzing Solar Assistant Web Application ==="
echo "Please run this script manually with:"
echo "ssh solar-assistant@172.16.109.214"
echo "Password: solar123"
echo ""
echo "Then run these commands:"
echo ""
cat << 'EOF'
# 1. Find web application location
echo "=== Web App Location ==="
sudo find /opt /var /usr -name "*.ex" -o -name "*.exs" 2>/dev/null | head -20
sudo find /opt /var /usr -name "phoenix" -o -name "solar_assistant" 2>/dev/null | head -20

# 2. Check running processes
echo "=== Running Processes ==="
ps aux | grep -E "beam|phoenix|elixir" | grep -v grep

# 3. Check web server configuration
echo "=== Web Server Config ==="
sudo ls -la /etc/nginx/sites-enabled/ 2>/dev/null || echo "No nginx"
sudo ls -la /etc/apache2/sites-enabled/ 2>/dev/null || echo "No apache"

# 4. Find Phoenix/Elixir app
echo "=== Phoenix App Location ==="
sudo find / -name "solar_assistant*.ex" 2>/dev/null | head -10
sudo find / -name "router.ex" 2>/dev/null | grep -i solar | head -10

# 5. Check systemd services
echo "=== Systemd Services ==="
sudo systemctl list-units | grep -i solar

# 6. Check listening ports
echo "=== Listening Ports ==="
sudo netstat -tlnp | grep -E ":80|:4000|:8080"

# 7. Database
echo "=== Database ==="
sudo -u postgres psql -l 2>/dev/null || echo "PostgreSQL not found"
ls -la /var/lib/mysql 2>/dev/null || echo "MySQL not found"

# 8. Application directory
echo "=== App Directory Structure ==="
if [ -d "/opt/solar_assistant" ]; then
    sudo ls -la /opt/solar_assistant/
    sudo ls -la /opt/solar_assistant/lib/ 2>/dev/null | head -10
    sudo ls -la /opt/solar_assistant/priv/static/ 2>/dev/null | head -10
fi

# 9. Environment variables
echo "=== Environment ==="
sudo cat /etc/environment | grep -i solar
sudo systemctl cat solar-assistant 2>/dev/null | grep -E "Environment|ExecStart"
EOF