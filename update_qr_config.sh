#!/bin/bash
# Update QR code configuration to use domain

set -e

echo "=========================================="
echo "Update QR Code Configuration"
echo "=========================================="
echo ""

APP_DIR="/home/giritharan/MES"
SERVICE_NAME="battery-mes"
DOMAIN="mes.pravaig.com"

echo "Current directory: $(pwd)"
echo "App directory: $APP_DIR"
echo ""

echo "Step 1: Checking if .env file exists..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo "✗ .env file not found at $APP_DIR/.env"
    exit 1
fi
echo "✓ .env file found"

echo ""
echo "Step 2: Backing up current .env file..."
cp $APP_DIR/.env $APP_DIR/.env.backup.$(date +%s)
echo "✓ Backup created"

echo ""
echo "Step 3: Current configuration:"
echo ""
echo "APP_BASE_URL:"
grep "^APP_BASE_URL=" $APP_DIR/.env || echo "(not set)"

echo ""
echo "ALLOWED_ORIGINS:"
grep "^ALLOWED_ORIGINS=" $APP_DIR/.env || echo "(not set)"

echo ""
echo "Step 4: Updating .env file with domain URL..."
# Update APP_BASE_URL to use domain
sed -i.bak 's|^APP_BASE_URL=.*|APP_BASE_URL=https://mes.pravaig.com|g' $APP_DIR/.env

# Update ALLOWED_ORIGINS to include domain
sed -i.bak 's|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://mes.pravaig.com,http://mes.pravaig.com,https://192.168.0.237:443,http://192.168.0.237,http://localhost:3000,http://localhost:8501|g' $APP_DIR/.env

echo "✓ .env file updated"

echo ""
echo "Step 5: New configuration:"
echo ""
echo "APP_BASE_URL:"
grep "^APP_BASE_URL=" $APP_DIR/.env

echo ""
echo "ALLOWED_ORIGINS:"
grep "^ALLOWED_ORIGINS=" $APP_DIR/.env

echo ""
echo "Step 6: Restarting application to apply changes..."
sudo systemctl restart $SERVICE_NAME

echo ""
echo "Step 7: Waiting for service to start..."
sleep 5

echo ""
echo "Step 8: Checking service status..."
sudo systemctl status $SERVICE_NAME --no-pager | head -10

echo ""
echo "=========================================="
echo "✓ QR Code Configuration Updated!"
echo "=========================================="
echo ""
echo "New QR codes will now use:"
echo "  https://mes.pravaig.com/entry/{battery_pack_id}"
echo ""
echo "Test:"
echo "  1. Create a new battery pack entry"
echo "  2. Generate QR code"
echo "  3. Scan with phone camera"
echo "  4. Should open: https://mes.pravaig.com/entry/..."
echo ""
