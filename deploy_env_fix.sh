#!/bin/bash

# Deploy .env loading fix to server
# This fixes QR codes to use domain instead of IP

set -e  # Exit on any error

echo "=================================="
echo "Deploying .env Loading Fix"
echo "=================================="

APP_DIR="/home/giritharan/MES"
VENV_DIR="$APP_DIR/venv"

# Step 1: Transfer updated application file
echo ""
echo "Step 1: Transferring updated application..."
scp app_unified_db.py giritharan@192.168.0.237:$APP_DIR/

# Step 2: Install python-dotenv on server
echo ""
echo "Step 2: Installing python-dotenv..."
ssh giritharan@192.168.0.237 << 'ENDSSH'
cd /home/giritharan/MES
source venv/bin/activate
pip install python-dotenv
deactivate
ENDSSH

# Step 3: Verify .env file configuration
echo ""
echo "Step 3: Verifying .env configuration..."
ssh giritharan@192.168.0.237 "grep APP_BASE_URL $APP_DIR/.env"

# Step 4: Restart the service
echo ""
echo "Step 4: Restarting battery-mes service..."
ssh giritharan@192.168.0.237 "sudo systemctl restart battery-mes"

# Step 5: Wait and check status
echo ""
echo "Waiting 5 seconds for service to start..."
sleep 5

ssh giritharan@192.168.0.237 "sudo systemctl status battery-mes --no-pager -l"

echo ""
echo "=================================="
echo "Deployment Complete!"
echo "=================================="
echo ""
echo "IMPORTANT:"
echo "1. QR codes will now use: https://mes.pravaig.com"
echo "2. Barcode scanner has simple Submit button"
echo "3. Old QR codes (already generated) will still use IP"
echo "4. NEW QR codes will use the domain"
echo ""
echo "Test by generating a NEW battery pack QR code!"
echo "=================================="
