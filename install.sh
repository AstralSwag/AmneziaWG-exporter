#!/bin/bash

# AmneziaWG Exporter installation script as systemd service

set -e

echo "Installing AmneziaWG Exporter..."

# Check root privileges
if [ "$EUID" -ne 0 ]; then 
    echo "Please run the script with root privileges (sudo)"
    exit 1
fi

# Install dependencies
echo "Installing Python dependencies..."
pip3 install prometheus-client --break-system-packages # Without venv

# Create directory
echo "Creating directory /opt/awg-exporter..."
mkdir -p /opt/awg-exporter

# Copy files
echo "Copying files..."
cp exporter.py /opt/awg-exporter/
cp peer_names.json /opt/awg-exporter/

# Set permissions
chmod +x /opt/awg-exporter/exporter.py

# Copy systemd unit file
echo "Installing systemd service..."
cp awg-exporter.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable and start service
echo "Starting service..."
systemctl enable awg-exporter.service
systemctl start awg-exporter.service

# Check status
echo ""
echo "Service status:"
systemctl status awg-exporter.service --no-pager

echo ""
echo "Installation completed!"
echo "Metrics available at http://localhost:9586/metrics"
echo ""
echo "Useful commands:"
echo "  systemctl status awg-exporter   - check status"
echo "  systemctl restart awg-exporter  - restart"
echo "  systemctl stop awg-exporter     - stop"
echo "  journalctl -u awg-exporter -f   - view logs"
echo ""
echo "Don't forget to edit /opt/awg-exporter/peer_names.json"
echo "to add names for your peers!"