#!/bin/bash
# Battery Pack MES - Complete HTTPS Setup with Nginx
# This script sets up a production-ready HTTPS configuration

set -e

echo "=========================================="
echo "Battery Pack MES - HTTPS Setup"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Revert Streamlit service to port 8501"
echo "  2. Install and configure Nginx"
echo "  3. Generate SSL certificate"
echo "  4. Configure reverse proxy (443 → 8501)"
echo "  5. Auto-redirect HTTP to HTTPS"
echo "  6. Enable camera functionality"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Configuration
APP_DIR="/home/giritharan/MES"
SERVICE_NAME="battery-mes"
SERVER_IP="192.168.0.237"

echo ""
echo "=========================================="
echo "Step 1: Updating service to port 8501"
echo "=========================================="
sudo systemctl stop $SERVICE_NAME

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

echo "Service updated to use port 8501 (localhost only)"

echo ""
echo "=========================================="
echo "Step 2: Installing Nginx"
echo "=========================================="
sudo apt update
sudo apt install -y nginx

echo ""
echo "=========================================="
echo "Step 3: Generating SSL certificate"
echo "=========================================="
sudo mkdir -p /etc/ssl/battery-mes
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/battery-mes/key.pem \
  -out /etc/ssl/battery-mes/cert.pem \
  -subj "/C=IN/ST=Karnataka/L=Bangalore/O=PDPL/OU=Manufacturing/CN=$SERVER_IP"

echo "SSL certificate generated"

echo ""
echo "=========================================="
echo "Step 4: Configuring Nginx reverse proxy"
echo "=========================================="
sudo tee /etc/nginx/sites-available/battery-mes > /dev/null << 'NGINX_EOF'
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
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

        # WebSocket support (required for Streamlit)
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

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name 192.168.0.237;

    return 301 https://$host$request_uri;
}
NGINX_EOF

echo "Nginx configuration created"

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
    sudo ufw allow 443/tcp comment 'Battery MES HTTPS'
    sudo ufw allow 80/tcp comment 'Battery MES HTTP redirect'
    # Remove old port 8501 rule if exists
    sudo ufw delete allow 8501/tcp 2>/dev/null || true
    echo "Firewall rules updated"
else
    echo "UFW not installed, skipping firewall configuration"
fi

echo ""
echo "=========================================="
echo "Step 8: Starting services"
echo "=========================================="
sudo systemctl daemon-reload
sudo systemctl restart $SERVICE_NAME
sudo systemctl enable nginx
sudo systemctl restart nginx

echo ""
echo "Step 9: Waiting for services to start..."
sleep 5

echo ""
echo "=========================================="
echo "Step 10: Checking service status"
echo "=========================================="
echo ""
echo "Battery MES Service:"
sudo systemctl status $SERVICE_NAME --no-pager | head -10

echo ""
echo "Nginx Service:"
sudo systemctl status nginx --no-pager | head -10

echo ""
echo "=========================================="
echo "HTTPS Setup Complete! ✓"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  HTTPS: https://$SERVER_IP (Primary)"
echo "  HTTP:  http://$SERVER_IP (Auto-redirects to HTTPS)"
echo ""
echo "✓ Camera functionality enabled"
echo "✓ Secure WebSocket connections"
echo "✓ Auto HTTP → HTTPS redirect"
echo ""
echo "⚠️  IMPORTANT: Self-signed Certificate"
echo "When accessing for the first time, users will see a security warning."
echo "Steps to proceed:"
echo "  1. Click 'Advanced' or 'Show Details'"
echo "  2. Click 'Proceed to $SERVER_IP' or 'Accept Risk'"
echo "  3. Bookmark the HTTPS URL"
echo ""
echo "Service Management:"
echo "  Check status:  sudo systemctl status battery-mes"
echo "  Check Nginx:   sudo systemctl status nginx"
echo "  View logs:     sudo journalctl -u battery-mes -f"
echo "  Nginx logs:    sudo tail -f /var/log/nginx/error.log"
echo ""
echo "Troubleshooting:"
echo "  Test backend:  curl http://127.0.0.1:8501"
echo "  Test HTTPS:    curl -k https://$SERVER_IP"
echo "  Nginx config:  sudo nginx -t"
echo ""
