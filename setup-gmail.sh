#!/bin/bash
# Setup script for Gmail integration

echo "Setting up Gmail integration for EG4-SRP Monitor..."

# Check if gmail_integration directory exists
if [ ! -d "../gmail_integration" ]; then
    echo "Error: gmail_integration directory not found at ../gmail_integration"
    echo "Please ensure the gmail_integration project is available"
    exit 1
fi

# Check if .env exists in gmail_integration
if [ ! -f "../gmail_integration/.env" ]; then
    echo "Warning: No .env file found in gmail_integration directory"
    echo "You'll need to run 'gmail-auth-setup' to configure Gmail credentials"
fi

# Copy gmail_integration to a temporary location for Docker build
echo "Copying gmail_integration for Docker build..."
cp -r ../gmail_integration ./gmail_integration_temp

echo "Gmail integration setup complete!"
echo "Now you can build the Docker image with: docker compose build"