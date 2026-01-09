#!/bin/bash
# Battery Pack MES - Fix Port 80 Permission Issue (v2)
# This script finds the real Python binary and grants capability to bind to privileged ports

set -e

echo "=========================================="
echo "Fix Port 80 Permission Issue (v2)"
echo "=========================================="
echo ""

# Configuration
APP_DIR="/home/giritharan/MES"
PYTHON_SYMLINK="$APP_DIR/venv/bin/python3"

echo "Step 1: Finding the real Python binary..."
echo "Symlink: $PYTHON_SYMLINK"

# Follow the symlink to find the real binary
REAL_PYTHON=$(readlink -f "$PYTHON_SYMLINK")
echo "Real binary: $REAL_PYTHON"

if [ ! -f "$REAL_PYTHON" ]; then
    echo "Error: Real Python binary not found at $REAL_PYTHON"
    exit 1
fi

echo ""
echo "Step 2: Granting capability to bind to privileged ports..."
echo "Running: sudo setcap 'cap_net_bind_service=+ep' $REAL_PYTHON"
sudo setcap 'cap_net_bind_service=+ep' "$REAL_PYTHON"

echo ""
echo "Step 3: Verifying capability..."
getcap "$REAL_PYTHON"

echo ""
echo "Step 4: Restarting battery-mes service..."
sudo systemctl restart battery-mes

echo ""
echo "Step 5: Waiting for service to start..."
sleep 5

echo ""
echo "Step 6: Checking service status..."
sudo systemctl status battery-mes --no-pager

echo ""
echo "=========================================="
echo "Fix Complete!"
echo "=========================================="
echo ""
echo "Your application should now be running on port 80"
echo "Access URL: http://192.168.0.237:80 or http://192.168.0.237"
echo ""
echo "To verify:"
echo "  curl http://localhost:80"
echo ""
