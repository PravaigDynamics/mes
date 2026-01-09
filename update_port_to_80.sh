#!/bin/bash
# Battery Pack MES - Update Port to 80 Script
# Run this script on the server to change from port 8501 to port 80

set -e

echo "=========================================="
echo "Battery Pack MES - Port Update to 80"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Stop the running service"
echo "  2. Update systemd service to use port 80"
echo "  3. Update firewall rules"
echo "  4. Restart the service"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Configuration
APP_DIR="/home/giritharan/MES"
SERVICE_NAME="battery-mes"

echo ""
echo "Step 1: Stopping the service..."
sudo systemctl stop $SERVICE_NAME

echo ""
echo "Step 2: Updating systemd service file..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<'EOF'
[Unit]
Description=Battery Pack MES Application
After=network.target

[Service]
Type=simple
User=giritharan
WorkingDirectory=/home/giritharan/MES
Environment="PATH=/home/giritharan/MES/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/giritharan/MES/venv/bin/streamlit run app_unified_db.py --server.port 80 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Service file updated successfully"

echo ""
echo "Step 3: Updating firewall rules..."
if command -v ufw &> /dev/null; then
    echo "UFW detected, updating firewall rules..."
    # Remove old rule if exists
    sudo ufw delete allow 8501/tcp 2>/dev/null || echo "Old rule not found, skipping..."
    # Add new rule
    sudo ufw allow 80/tcp comment 'Battery Pack MES'
    echo "Firewall rule updated"
else
    echo "UFW not installed, skipping firewall configuration"
fi

echo ""
echo "Step 4: Reloading systemd daemon..."
sudo systemctl daemon-reload

echo ""
echo "Step 5: Starting the service..."
sudo systemctl start $SERVICE_NAME

echo ""
echo "Step 6: Waiting for service to start..."
sleep 3

echo ""
echo "Step 7: Checking service status..."
sudo systemctl status $SERVICE_NAME --no-pager

echo ""
echo "=========================================="
echo "Port Update Complete!"
echo "=========================================="
echo ""
echo "Application Information:"
echo "  - New Access URL: http://192.168.0.237:80"
echo "  - Service Name: $SERVICE_NAME"
echo "  - Status: Active"
echo ""
echo "Service Management Commands:"
echo "  - Status:  sudo systemctl status $SERVICE_NAME"
echo "  - Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  - Start:   sudo systemctl start $SERVICE_NAME"
echo "  - Restart: sudo systemctl restart $SERVICE_NAME"
echo "  - Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Testing:"
echo "  - From VM: curl http://localhost:80"
echo "  - From network: http://192.168.0.237:80"
echo ""
echo "NOTE: Port 80 requires sudo/root privileges to run."
echo "The service runs as user 'giritharan' but systemd handles the port binding."
echo ""
