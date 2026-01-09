#!/bin/bash
# Battery Pack MES - VM Deployment Script
# This script sets up the application on the VM for production use
# with support for multiple concurrent users

set -e  # Exit on error

echo "=========================================="
echo "Battery Pack MES - VM Deployment"
echo "=========================================="
echo ""

# Configuration
APP_DIR="/home/giritharan/MES"
VM_USER="giritharan"
PYTHON_VERSION="python3"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Step 1: Checking system requirements...${NC}"
# Check if Python is installed
if ! command -v $PYTHON_VERSION &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Installing...${NC}"
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# Check Python version
PYTHON_VER=$($PYTHON_VERSION --version)
echo -e "${GREEN}Python version: $PYTHON_VER${NC}"

echo ""
echo -e "${GREEN}Step 2: Creating application directory...${NC}"
sudo mkdir -p $APP_DIR
sudo chown $VM_USER:$VM_USER $APP_DIR
cd $APP_DIR

echo ""
echo -e "${GREEN}Step 3: Setting up Python virtual environment...${NC}"
if [ -d "venv" ]; then
    echo "Virtual environment already exists, removing old one..."
    rm -rf venv
fi

$PYTHON_VERSION -m venv venv
source venv/bin/activate

echo ""
echo -e "${GREEN}Step 4: Upgrading pip...${NC}"
pip install --upgrade pip

echo ""
echo -e "${GREEN}Step 5: Installing dependencies...${NC}"
if [ -f "requirements_new.txt" ]; then
    pip install -r requirements_new.txt
else
    echo -e "${RED}requirements_new.txt not found!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Step 6: Setting up directories...${NC}"
mkdir -p qr_codes
mkdir -p excel_reports
mkdir -p backups
mkdir -p logs

echo ""
echo -e "${GREEN}Step 7: Initializing database...${NC}"
# Create database if it doesn't exist
if [ ! -f "battery_mes.db" ]; then
    echo "Creating new database..."
    $PYTHON_VERSION -c "from database import init_database; init_database()"
else
    echo "Database already exists, skipping initialization..."
fi

echo ""
echo -e "${GREEN}Step 8: Setting permissions...${NC}"
chmod -R 755 $APP_DIR
chmod 644 battery_mes.db 2>/dev/null || true

echo ""
echo -e "${GREEN}Step 9: Configuring firewall...${NC}"
# Check if ufw is installed
if command -v ufw &> /dev/null; then
    echo "Configuring UFW firewall..."
    sudo ufw allow 80/tcp comment 'Battery Pack MES'
    echo "Firewall rule added for port 80"
else
    echo "UFW not installed, skipping firewall configuration"
fi

echo ""
echo -e "${GREEN}Step 10: Creating systemd service...${NC}"

# Create systemd service file
sudo tee /etc/systemd/system/battery-mes.service > /dev/null <<EOF
[Unit]
Description=Battery Pack MES Application
After=network.target

[Service]
Type=simple
User=$VM_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$APP_DIR/venv/bin/streamlit run app_unified_db.py --server.port 80 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo -e "${GREEN}Step 11: Enabling and starting service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable battery-mes
sudo systemctl restart battery-mes

echo ""
echo -e "${GREEN}Step 12: Checking service status...${NC}"
sleep 3
sudo systemctl status battery-mes --no-pager || true

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Application Information:"
echo "  - Service Name: battery-mes"
echo "  - Installation Directory: $APP_DIR"
echo "  - Database: $APP_DIR/battery_mes.db"
echo "  - Access URL: http://192.168.0.237:80"
echo ""
echo "Service Management Commands:"
echo "  - Check status: sudo systemctl status battery-mes"
echo "  - Stop service: sudo systemctl stop battery-mes"
echo "  - Start service: sudo systemctl start battery-mes"
echo "  - Restart service: sudo systemctl restart battery-mes"
echo "  - View logs: sudo journalctl -u battery-mes -f"
echo ""
echo "Testing:"
echo "  - From VM: curl http://localhost:80"
echo "  - From network: http://192.168.0.237:80"
echo ""
echo -e "${YELLOW}Please test the application and verify concurrent access!${NC}"
echo ""
