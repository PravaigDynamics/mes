#!/bin/bash
# Battery Pack MES - Complete Setup (requires sudo)
# Run this script on the VM to set up systemd service and firewall

set -e

echo "==========================================="
echo "Battery Pack MES - Final Setup"
echo "==========================================="
echo ""
echo "This script will:"
echo "  1. Stop any running Streamlit processes"
echo "  2. Create systemd service for auto-start"
echo "  3. Configure firewall (if ufw is installed)"
echo "  4. Enable and start the service"
echo ""

# Kill existing streamlit processes
echo "Step 1: Stopping existing Streamlit processes..."
pkill -f "streamlit run app_unified_db.py" || echo "No existing processes found"
sleep 2

# Create systemd service file
echo ""
echo "Step 2: Creating systemd service..."
sudo tee /etc/systemd/system/battery-mes.service > /dev/null <<'EOF'
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

echo "Service file created successfully"

# Configure firewall
echo ""
echo "Step 3: Configuring firewall..."
if command -v ufw &> /dev/null; then
    echo "UFW detected, adding firewall rule..."
    sudo ufw allow 80/tcp comment 'Battery Pack MES'
    echo "Firewall rule added"
else
    echo "UFW not installed, skipping firewall configuration"
fi

# Reload systemd
echo ""
echo "Step 4: Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service
echo ""
echo "Step 5: Enabling service for auto-start..."
sudo systemctl enable battery-mes

# Start service
echo ""
echo "Step 6: Starting Battery MES service..."
sudo systemctl start battery-mes

# Wait a moment
sleep 3

# Check status
echo ""
echo "Step 7: Checking service status..."
sudo systemctl status battery-mes --no-pager

echo ""
echo "==========================================="
echo "Setup Complete!"
echo "==========================================="
echo ""
echo "Application Information:"
echo "  - Access URL: http://192.168.0.237:80"
echo "  - Service Name: battery-mes"
echo "  - Status: Active"
echo ""
echo "Service Management Commands:"
echo "  - Status:  sudo systemctl status battery-mes"
echo "  - Stop:    sudo systemctl stop battery-mes"
echo "  - Start:   sudo systemctl start battery-mes"
echo "  - Restart: sudo systemctl restart battery-mes"
echo "  - Logs:    sudo journalctl -u battery-mes -f"
echo ""
echo "Next Steps:"
echo "  1. Open browser to: http://192.168.0.237:80"
echo "  2. Test creating QR codes"
echo "  3. Test data entry with multiple users"
echo "  4. Verify concurrent access works"
echo ""
echo "The service will now start automatically on VM reboot."
echo ""
