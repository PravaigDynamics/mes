#!/bin/bash
# Battery Pack MES - Dual HTTP/HTTPS Setup
# HTTP on port 80, HTTPS on port 8443, with automatic fallback

set -e

echo "=========================================="
echo "Battery Pack MES - Dual HTTP/HTTPS Setup"
echo "=========================================="
echo ""
echo "This script will configure:"
echo "  - HTTP:  Port 80  (http://192.168.0.237)"
echo "  - HTTPS: Port 8443 (https://192.168.0.237:8443)"
echo "  - Backend: Streamlit on localhost:8501"
echo "  - No auto-redirect (user choice)"
echo ""
echo "Benefits:"
echo "  ✓ Camera works on HTTPS (port 8443)"
echo "  ✓ HTTP fallback on port 80"
echo "  ✓ Both use same backend"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Configuration
APP_DIR="/home/giritharan/MES"
SERVICE_NAME="battery-mes"
SERVER_IP="192.168.0.237"

echo ""
echo "=========================================="
echo "Step 1: Configuring Streamlit service"
echo "=========================================="
sudo systemctl stop $SERVICE_NAME 2>/dev/null || true

# Remove capability from Python if set
REAL_PYTHON=$(readlink -f $APP_DIR/venv/bin/python3)
sudo setcap -r "$REAL_PYTHON" 2>/dev/null || true

sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Battery Pack MES Application
After=network.target

[Service]
Type=simple
User=giritharan
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$APP_DIR/venv/bin/streamlit run app_unified_db.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Streamlit configured on localhost:8501"

echo ""
echo "=========================================="
echo "Step 2: Installing Nginx"
echo "=========================================="
if ! command -v nginx &> /dev/null; then
    sudo apt update
    sudo apt install -y nginx
    echo "✓ Nginx installed"
else
    echo "✓ Nginx already installed"
fi

echo ""
echo "=========================================="
echo "Step 3: Generating SSL certificate"
echo "=========================================="
sudo mkdir -p /etc/ssl/battery-mes
if [ ! -f /etc/ssl/battery-mes/cert.pem ]; then
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout /etc/ssl/battery-mes/key.pem \
      -out /etc/ssl/battery-mes/cert.pem \
      -subj "/C=IN/ST=Karnataka/L=Bangalore/O=PDPL/OU=Manufacturing/CN=$SERVER_IP"
    echo "✓ SSL certificate generated"
else
    echo "✓ SSL certificate already exists"
fi

echo ""
echo "=========================================="
echo "Step 4: Configuring Nginx (HTTP + HTTPS)"
echo "=========================================="
sudo tee /etc/nginx/sites-available/battery-mes > /dev/null << 'NGINX_EOF'
# HTTP Server - Port 80
server {
    listen 80;
    listen [::]:80;
    server_name 192.168.0.237;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_read_timeout 86400;
        proxy_connect_timeout 86400;
        proxy_send_timeout 86400;
    }
}

# HTTPS Server - Port 8443
server {
    listen 8443 ssl http2;
    listen [::]:8443 ssl http2;
    server_name 192.168.0.237;

    ssl_certificate /etc/ssl/battery-mes/cert.pem;
    ssl_certificate_key /etc/ssl/battery-mes/key.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_read_timeout 86400;
        proxy_connect_timeout 86400;
        proxy_send_timeout 86400;
    }
}
NGINX_EOF

echo "✓ Nginx configured for both HTTP and HTTPS"

echo ""
echo "=========================================="
echo "Step 5: Enabling Nginx site"
echo "=========================================="
sudo ln -sf /etc/nginx/sites-available/battery-mes /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

echo ""
echo "=========================================="
echo "Step 6: Testing Nginx configuration"
echo "=========================================="
sudo nginx -t

echo ""
echo "=========================================="
echo "Step 7: Configuring firewall"
echo "=========================================="
if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp comment 'Battery MES HTTP'
    sudo ufw allow 8443/tcp comment 'Battery MES HTTPS'
    # Remove old rules
    sudo ufw delete allow 8501/tcp 2>/dev/null || true
    sudo ufw delete allow 443/tcp 2>/dev/null || true
    echo "✓ Firewall rules updated"
else
    echo "⚠ UFW not installed, skipping firewall configuration"
fi

echo ""
echo "=========================================="
echo "Step 8: Starting services"
echo "=========================================="
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME
sudo systemctl enable nginx
sudo systemctl restart nginx

echo ""
echo "Step 9: Waiting for services to start..."
sleep 5

echo ""
echo "=========================================="
echo "Step 10: Verifying services"
echo "=========================================="
echo ""
echo "Streamlit Service:"
sudo systemctl status $SERVICE_NAME --no-pager | head -10

echo ""
echo "Nginx Service:"
sudo systemctl status nginx --no-pager | head -10

echo ""
echo "=========================================="
echo "✓ Dual HTTP/HTTPS Setup Complete!"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  HTTP:  http://$SERVER_IP (port 80)"
echo "  HTTPS: https://$SERVER_IP:8443"
echo ""
echo "Usage Guidelines:"
echo "  • Use HTTPS for camera functionality"
echo "  • Use HTTP as fallback if HTTPS has issues"
echo "  • Both URLs access the same application"
echo "  • QR codes will use HTTPS by default"
echo ""
echo "⚠️  HTTPS First-Time Access:"
echo "  1. Browser will show 'Not secure' warning"
echo "  2. Click 'Advanced' or 'Show Details'"
echo "  3. Click 'Proceed to $SERVER_IP'"
echo "  4. Bookmark the HTTPS URL"
echo ""
echo "Service Management:"
echo "  Streamlit:  sudo systemctl status $SERVICE_NAME"
echo "  Nginx:      sudo systemctl status nginx"
echo "  Logs:       sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Testing:"
echo "  Backend:    curl http://127.0.0.1:8501"
echo "  HTTP:       curl http://$SERVER_IP"
echo "  HTTPS:      curl -k https://$SERVER_IP:8443"
echo ""
echo "Troubleshooting:"
echo "  Check ports: sudo netstat -tlnp | grep -E '(80|8443|8501)'"
echo "  Nginx test:  sudo nginx -t"
echo "  Nginx logs:  sudo tail -f /var/log/nginx/error.log"
echo ""
