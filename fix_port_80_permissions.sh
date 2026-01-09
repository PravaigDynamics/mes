#!/bin/bash
# Battery Pack MES - Fix Port 80 Permission Issue
# This script grants the Python binary capability to bind to privileged ports

set -e

echo "=========================================="
echo "Fix Port 80 Permission Issue"
echo "=========================================="
echo ""

# Configuration
APP_DIR="/home/giritharan/MES"
PYTHON_BIN="$APP_DIR/venv/bin/python3"

echo "Step 1: Checking Python binary location..."
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Error: Python binary not found at $PYTHON_BIN"
    exit 1
fi

echo "Found: $PYTHON_BIN"

echo ""
echo "Step 2: Granting capability to bind to privileged ports..."
echo "Running: sudo setcap 'cap_net_bind_service=+ep' $PYTHON_BIN"
sudo setcap 'cap_net_bind_service=+ep' "$PYTHON_BIN"

echo ""
echo "Step 3: Verifying capability..."
getcap "$PYTHON_BIN"

echo ""
echo "Step 4: Restarting battery-mes service..."
sudo systemctl restart battery-mes

echo ""
echo "Step 5: Waiting for service to start..."
sleep 3

echo ""
echo "Step 6: Checking service status..."
sudo systemctl status battery-mes --no-pager

echo ""
echo "=========================================="
echo "Fix Complete!"
echo "=========================================="
echo ""
echo "Your application should now be running on port 80"
echo "Access URL: http://192.168.0.237:80"
echo ""
