#!/bin/bash
# Deploy QR code configuration-driven fix

set -e

echo "=========================================="
echo "Deploy QR Code Configuration Fix"
echo "=========================================="
echo ""

APP_DIR="/home/giritharan/MES"
SERVICE_NAME="battery-mes"

echo "Step 1: Creating .streamlit directory if not exists..."
mkdir -p $APP_DIR/.streamlit

echo ""
echo "Step 2: Moving config.toml to correct location..."
if [ -f "$APP_DIR/config.toml" ]; then
    mv $APP_DIR/config.toml $APP_DIR/.streamlit/config.toml
    echo "✓ Moved config.toml to .streamlit directory"
else
    echo "⚠ config.toml not found in $APP_DIR (may already be in place)"
fi

echo ""
echo "Step 3: Verifying files..."
ls -la $APP_DIR/app_unified_db.py
ls -la $APP_DIR/.streamlit/config.toml

echo ""
echo "Step 4: Checking APP_BASE_URL in .env..."
grep "APP_BASE_URL" $APP_DIR/.env | grep -v "^#"

echo ""
echo "Step 5: Restarting service..."
sudo systemctl restart $SERVICE_NAME

echo ""
echo "Step 6: Waiting for service to start..."
sleep 5

echo ""
echo "Step 7: Checking service status..."
sudo systemctl status $SERVICE_NAME --no-pager | head -15

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Changes deployed:"
echo "  ✓ QR codes now read from APP_BASE_URL environment variable"
echo "  ✓ Streamlit configured to use mes.pravaig.com:443"
echo "  ✓ Configuration-driven (no more hardcoded URLs)"
echo ""
echo "Test:"
echo "  1. Create a new battery pack entry"
echo "  2. Generate QR code"
echo "  3. QR code will use URL from .env file"
echo "  4. Scan with phone - should open mes.pravaig.com"
echo ""
echo "To change URL in future:"
echo "  1. Edit /home/giritharan/MES/.env"
echo "  2. Update APP_BASE_URL=https://your-new-domain.com"
echo "  3. Restart service: sudo systemctl restart battery-mes"
echo ""
