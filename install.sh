#!/bin/bash

# EG4-SRP Monitor Installation Script
# This script sets up the EG4-SRP Monitor with all dependencies and systemd service

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root. Please run as a regular user."
        exit 1
    fi
}

# Check Python version
check_python() {
    log_info "Checking Python version..."
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    required_version="3.8"
    
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_error "Python $python_version found, but Python $required_version or higher is required."
        exit 1
    fi
    
    log_success "Python $python_version found"
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    # Update package list
    sudo apt update
    
    # Install required packages
    sudo apt install -y \
        python3-venv \
        python3-pip \
        curl \
        wget \
        git \
        systemd
    
    log_success "System dependencies installed"
}

# Set up virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    log_success "Virtual environment ready"
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install requirements
    pip install -r requirements.txt
    
    # Install Playwright browsers
    playwright install chromium
    
    log_success "Python dependencies installed"
}

# Create required directories
create_directories() {
    log_info "Creating required directories..."
    
    mkdir -p logs
    mkdir -p config
    mkdir -p downloads
    mkdir -p ~/.gmail_send
    
    # Set proper permissions
    chmod 755 logs config downloads
    chmod 700 ~/.gmail_send
    
    log_success "Directories created"
}

# Set up systemd service
setup_service() {
    log_info "Setting up systemd service..."
    
    # Get current user and working directory
    current_user=$(whoami)
    current_dir=$(pwd)
    
    # Update service file with correct paths
    sed -i "s|User=jeremy|User=$current_user|g" eg4-srp-monitor.service
    sed -i "s|Group=jeremy|Group=$current_user|g" eg4-srp-monitor.service
    sed -i "s|WorkingDirectory=/mnt/data/src/eg4-srp-monitor|WorkingDirectory=$current_dir|g" eg4-srp-monitor.service
    sed -i "s|Environment=PATH=/mnt/data/src/eg4-srp-monitor/venv/bin|Environment=PATH=$current_dir/venv/bin|g" eg4-srp-monitor.service
    sed -i "s|ExecStart=/mnt/data/src/eg4-srp-monitor/venv/bin/python app.py|ExecStart=$current_dir/venv/bin/python app.py|g" eg4-srp-monitor.service
    sed -i "s|ReadWritePaths=/mnt/data/src/eg4-srp-monitor|ReadWritePaths=$current_dir|g" eg4-srp-monitor.service
    sed -i "s|ReadWritePaths=/home/jeremy/.gmail_send|ReadWritePaths=/home/$current_user/.gmail_send|g" eg4-srp-monitor.service
    
    # Copy service file to systemd
    sudo cp eg4-srp-monitor.service /etc/systemd/system/
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable eg4-srp-monitor
    
    log_success "Systemd service configured"
}

# Test installation
test_installation() {
    log_info "Testing installation..."
    
    # Test Python imports
    source venv/bin/activate
    python3 -c "
import flask
import flask_socketio
import playwright
import requests
print('All Python dependencies imported successfully')
"
    
    # Test Playwright browser
    python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    browser.close()
print('Playwright browser test successful')
"
    
    log_success "Installation test passed"
}

# Main installation function
main() {
    echo "================================================="
    echo "       EG4-SRP Monitor Installation Script      "
    echo "================================================="
    echo ""
    
    check_root
    check_python
    install_system_deps
    setup_venv
    install_python_deps
    create_directories
    setup_service
    test_installation
    
    echo ""
    echo "================================================="
    log_success "Installation completed successfully!"
    echo "================================================="
    echo ""
    echo "Next steps:"
    echo "1. Configure your credentials:"
    echo "   - Start the application: python app.py"
    echo "   - Navigate to: http://localhost:5002"
    echo "   - Go to Configuration tab and enter your credentials"
    echo ""
    echo "2. Start the service:"
    echo "   sudo systemctl start eg4-srp-monitor"
    echo ""
    echo "3. Check service status:"
    echo "   sudo systemctl status eg4-srp-monitor"
    echo ""
    echo "4. View logs:"
    echo "   sudo journalctl -u eg4-srp-monitor -f"
    echo ""
    echo "For more information, see README.md"
    echo ""
}

# Run main function
main "$@"