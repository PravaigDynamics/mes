#!/bin/bash
# Fix QR code generation to use domain instead of IP

set -e

echo "=========================================="
echo "Fix QR Code Domain Configuration"
echo "=========================================="
echo ""

APP_DIR="/home/giritharan/MES"
SERVICE_NAME="battery-mes"
DOMAIN="mes.pravaig.com"

echo "Step 1: Pulling latest code from GitHub..."
cd $APP_DIR
git stash 2>/dev/null || true  # Save any local changes
git pull origin master
echo "✓ Code updated"

echo ""
echo "Step 2: Backing up current .env file..."
cp $APP_DIR/.env $APP_DIR/.env.backup.$(date +%s)
echo "✓ Backup created"

echo ""
echo "Step 3: Updating .env file with domain URL..."
# Update APP_BASE_URL to use domain
sudo sed -i 's|APP_BASE_URL=.*|APP_BASE_URL=https://mes.pravaig.com|g' $APP_DIR/.env

# Update ALLOWED_ORIGINS to include domain
sudo sed -i 's|ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://mes.pravaig.com,http://mes.pravaig.com,https://192.168.0.237:443,http://192.168.0.237,http://localhost:3000,http://localhost:8501|g' $APP_DIR/.env

echo "✓ .env file updated"

echo ""
echo "Step 4: Verifying changes..."
echo ""
echo "APP_BASE_URL:"
grep "APP_BASE_URL" $APP_DIR/.env | grep -v "^#"

echo ""
echo "ALLOWED_ORIGINS:"
grep "ALLOWED_ORIGINS" $APP_DIR/.env | grep -v "^#"

echo ""
echo "Step 5: Restarting application to apply changes..."
sudo systemctl restart $SERVICE_NAME

echo ""
echo "Step 6: Waiting for service to start..."
sleep 5

echo ""
echo "Step 7: Checking service status..."
sudo systemctl status $SERVICE_NAME --no-pager | head -10

echo ""
echo "=========================================="
echo "✓ QR Code Configuration Fixed!"
echo "=========================================="
echo ""
echo "New QR codes will now use:"
echo "  https://mes.pravaig.com/entry/{battery_pack_id}"
echo ""
echo "Old QR codes (already printed) will continue to work if:"
echo "  - They point to IP: Will redirect to domain"
echo "  - Nginx is configured to handle both"
echo ""
echo "Test:"
echo "  1. Create a new battery pack entry"
echo "  2. Generate QR code"
echo "  3. Scan with phone camera"
echo "  4. Should open: https://mes.pravaig.com/entry/..."
echo ""
