#!/bin/bash

# Run this script ON THE SERVER to install python-dotenv
# This fixes QR codes to use domain instead of IP

echo "Installing python-dotenv..."
cd /home/giritharan/MES
source venv/bin/activate
pip install python-dotenv
deactivate

echo ""
echo "Restarting service..."
sudo systemctl restart battery-mes

echo ""
echo "Waiting for service to start..."
sleep 5

echo ""
echo "Service status:"
sudo systemctl status battery-mes --no-pager -l

echo ""
echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo "QR codes will now use: https://mes.pravaig.com"
echo "Test by generating a NEW battery pack!"
