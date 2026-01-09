#!/bin/bash
# Battery Pack MES - Domain-based HTTPS Setup
# Configure mes.pravaig.com with SSL/TLS

set -e

echo "=========================================="
echo "Battery Pack MES - Domain Setup"
echo "=========================================="
echo ""
echo "Domain: mes.pravaig.com"
echo "IP: 192.168.0.237"
echo ""
echo "This script will configure:"
echo "  - HTTPS on port 443 (mes.pravaig.com)"
echo "  - HTTP on port 80 (auto-redirect to HTTPS)"
echo "  - Streamlit backend on localhost:8501"
echo ""
echo "Prerequisites:"
echo "  1. DNS A record: mes.pravaig.com → 192.168.0.237"
echo "  2. Firewall allows ports 80, 443"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Configuration
APP_DIR="/home/giritharan/MES"
SERVICE_NAME="battery-mes"
DOMAIN="mes.pravaig.com"
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

# Generate certificate for domain
if [ ! -f /etc/ssl/battery-mes/cert.pem ]; then
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout /etc/ssl/battery-mes/key.pem \
      -out /etc/ssl/battery-mes/cert.pem \
      -subj "/C=IN/ST=Karnataka/L=Bangalore/O=Pravaig Dynamics/OU=Manufacturing/CN=$DOMAIN"
    echo "✓ SSL certificate generated for $DOMAIN"
else
    echo "✓ SSL certificate already exists"
fi

echo ""
echo "=========================================="
echo "Step 4: Configuring Nginx for domain"
echo "=========================================="
sudo tee /etc/nginx/sites-available/battery-mes > /dev/null << 'NGINX_EOF'
# HTTPS Server - Port 443 (Primary)
server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    server_name mes.pravaig.com 192.168.0.237;

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

    # Logging
    access_log /var/log/nginx/battery-mes-access.log;
    error_log /var/log/nginx/battery-mes-error.log;

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

# HTTP Server - Port 80 (Redirect to HTTPS)
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name mes.pravaig.com 192.168.0.237;

    # Redirect all HTTP traffic to HTTPS
    return 301 https://$host$request_uri;
}
NGINX_EOF

echo "✓ Nginx configured for $DOMAIN"

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
    # Remove old rules
    sudo ufw delete allow 8501/tcp 2>/dev/null || true
    sudo ufw delete allow 8443/tcp 2>/dev/null || true
    sudo ufw delete allow 8081/tcp 2>/dev/null || true
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
echo "✓ Domain Setup Complete!"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  Primary:  https://mes.pravaig.com"
echo "  IP-based: https://$SERVER_IP"
echo "  HTTP:     http://mes.pravaig.com (redirects to HTTPS)"
echo ""
echo "✓ Camera functionality enabled"
echo "✓ Secure HTTPS connections"
echo "✓ Auto HTTP → HTTPS redirect"
echo "✓ WebSocket support"
echo ""
echo "DNS Configuration (verify):"
echo "  Record Type: A"
echo "  Name: mes.pravaig.com"
echo "  Value: $SERVER_IP"
echo "  TTL: 3600"
echo ""
echo "⚠️  HTTPS Certificate Warning:"
echo "Self-signed certificate will show security warnings."
echo "To fix:"
echo "  1. Click 'Advanced' in browser"
echo "  2. Click 'Proceed to mes.pravaig.com'"
echo "  3. Or install Let's Encrypt certificate (recommended)"
echo ""
echo "Let's Encrypt Certificate (Optional):"
echo "  sudo apt install certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d mes.pravaig.com"
echo ""
echo "Service Management:"
echo "  Streamlit:  sudo systemctl status $SERVICE_NAME"
echo "  Nginx:      sudo systemctl status nginx"
echo "  Logs:       sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Testing:"
echo "  Backend:    curl http://127.0.0.1:8501"
echo "  Domain:     curl -k https://mes.pravaig.com"
echo "  IP:         curl -k https://$SERVER_IP"
echo ""
echo "Troubleshooting:"
echo "  Check DNS:  nslookup mes.pravaig.com"
echo "  Check DNS:  dig mes.pravaig.com"
echo "  Nginx test: sudo nginx -t"
echo "  Nginx logs: sudo tail -f /var/log/nginx/error.log"
echo ""
