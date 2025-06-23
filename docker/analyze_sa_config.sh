#!/bin/bash
# SSH commands to analyze Solar Assistant configuration

echo "=== Solar Assistant Configuration Analysis ==="
echo "Please SSH into the Solar Assistant and run these commands:"
echo ""
echo "ssh solar-assistant@172.16.109.214"
echo "Password: solar123"
echo ""
echo "Then execute:"
cat << 'EOF'

# 1. Find Solar Assistant app directory
echo "=== Finding Solar Assistant Application ==="
sudo find /opt /var/www /home -name "solar_assistant*" -type d 2>/dev/null | head -10

# 2. Check for Phoenix app structure
echo -e "\n=== Phoenix Application Structure ==="
if [ -d "/opt/solar_assistant" ]; then
    sudo ls -la /opt/solar_assistant/
    echo -e "\n--- Config files ---"
    sudo find /opt/solar_assistant -name "*.exs" -o -name "config.exs" | head -10
    echo -e "\n--- Templates ---"
    sudo find /opt/solar_assistant -name "*.html.eex" -o -name "*.html.leex" | grep -i config | head -10
fi

# 3. Check systemd service
echo -e "\n=== Systemd Service Configuration ==="
sudo systemctl status solar-assistant | head -20
sudo systemctl cat solar-assistant | grep -E "ExecStart|WorkingDirectory|Environment"

# 4. Check for configuration storage
echo -e "\n=== Configuration Storage ==="
# Check PostgreSQL
sudo -u postgres psql -l 2>/dev/null | grep -i solar || echo "No PostgreSQL database found"

# Check for SQLite
sudo find / -name "*.db" -o -name "*.sqlite*" 2>/dev/null | grep -i solar | head -5

# Check for config files
sudo find /etc /opt /var -name "*solar*.conf" -o -name "*solar*.json" -o -name "*solar*.yaml" 2>/dev/null | head -10

# 5. Check Elixir/Phoenix processes
echo -e "\n=== Running Processes ==="
ps aux | grep -E "beam|elixir|phoenix" | grep -v grep

# 6. Network ports
echo -e "\n=== Network Listening Ports ==="
sudo netstat -tlnp | grep -E ":80|:4000|:8080|beam"

# 7. Look for inverter configuration
echo -e "\n=== Inverter Configuration ==="
sudo grep -r "inverter" /opt/solar_assistant/priv 2>/dev/null | grep -i "ip\|address\|host" | head -10

# 8. Environment variables
echo -e "\n=== Environment Variables ==="
sudo cat /etc/environment | grep -i solar
sudo grep -r "DATABASE_URL\|SECRET_KEY" /opt/solar_assistant 2>/dev/null | head -5

# 9. Web assets
echo -e "\n=== Web Assets ==="
if [ -d "/opt/solar_assistant/priv/static" ]; then
    sudo ls -la /opt/solar_assistant/priv/static/
    sudo find /opt/solar_assistant/priv/static -name "*.js" | grep -i config | head -5
fi

# 10. Live view files
echo -e "\n=== LiveView Configuration Files ==="
sudo find /opt/solar_assistant -name "*configuration*" -o -name "*config*live*" 2>/dev/null | grep -E "\.ex$|\.exs$" | head -10

EOF

echo -e "\n\nAlternatively, run this one-liner after SSH:"
echo 'sudo find /opt -name "solar_assistant" -type d -exec ls -la {} \; 2>/dev/null | head -50'