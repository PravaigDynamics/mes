#!/bin/bash
# Battery Pack MES - Production SSL Setup
# Professional configuration for mes.pravaig.com
# Fixes domain redirect issues and configures proper SSL

set -e

echo "=========================================="
echo "Battery Pack MES - Production SSL Setup"
echo "=========================================="
echo ""
echo "Domain: mes.pravaig.com"
echo "Server: 192.168.0.237"
echo ""
echo "This script will:"
echo "  1. Generate proper SSL certificate for domain"
echo "  2. Configure Nginx to preserve domain name"
echo "  3. Fix redirect issues (domain → IP)"
echo "  4. Configure all ports professionally"
echo "  5. Enable camera functionality"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Configuration
APP_DIR="/home/giritharan/MES"
SERVICE_NAME="battery-mes"
DOMAIN="mes.pravaig.com"
SERVER_IP="192.168.0.237"

echo ""
echo "=========================================="
echo "Step 1: Stopping services"
echo "=========================================="
sudo systemctl stop nginx 2>/dev/null || true
sudo systemctl stop $SERVICE_NAME 2>/dev/null || true

echo ""
echo "=========================================="
echo "Step 2: Configuring Streamlit service"
echo "=========================================="

# Remove Python capability if set
REAL_PYTHON=$(readlink -f $APP_DIR/venv/bin/python3 2>/dev/null || echo "")
if [ -n "$REAL_PYTHON" ]; then
    sudo setcap -r "$REAL_PYTHON" 2>/dev/null || true
fi

sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Battery Pack MES Application
After=network.target

[Service]
Type=simple
User=giritharan
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$APP_DIR/venv/bin/streamlit run app_unified_db.py --server.port 8501 --server.address 127.0.0.1 --server.headless true --server.enableCORS=false --server.enableXsrfProtection=false
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Streamlit service configured (localhost:8501)"

echo ""
echo "=========================================="
echo "Step 3: Installing Nginx"
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
echo "Step 4: Generating SSL certificate"
echo "=========================================="
sudo mkdir -p /etc/ssl/battery-mes

# Generate proper SSL certificate with Subject Alternative Names
echo "Creating OpenSSL configuration..."
sudo tee /etc/ssl/battery-mes/openssl.cnf > /dev/null <<SSLEOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
x509_extensions = v3_req
distinguished_name = dn

[dn]
C = IN
ST = Karnataka
L = Bangalore
O = Pravaig Dynamics
OU = Manufacturing Execution Systems
CN = $DOMAIN

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = www.$DOMAIN
IP.1 = $SERVER_IP
SSLEOF

# Generate certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/battery-mes/key.pem \
  -out /etc/ssl/battery-mes/cert.pem \
  -config /etc/ssl/battery-mes/openssl.cnf \
  -extensions v3_req

echo "✓ SSL certificate generated with SANs"

# Set proper permissions
sudo chmod 600 /etc/ssl/battery-mes/key.pem
sudo chmod 644 /etc/ssl/battery-mes/cert.pem

echo ""
echo "=========================================="
echo "Step 5: Configuring Nginx (Professional)"
echo "=========================================="

# Create optimized Nginx configuration
sudo tee /etc/nginx/sites-available/battery-mes > /dev/null << 'NGINX_EOF'
# Upstream backend
upstream streamlit_backend {
    server 127.0.0.1:8501;
    keepalive 32;
}

# HTTPS Server - Port 443 (Primary)
server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;

    # Server names - DOMAIN FIRST (important!)
    server_name mes.pravaig.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/battery-mes/cert.pem;
    ssl_certificate_key /etc/ssl/battery-mes/key.pem;

    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/battery-mes-access.log;
    error_log /var/log/nginx/battery-mes-error.log warn;

    # Client settings
    client_max_body_size 100M;
    client_body_timeout 120s;

    location / {
        # Proxy to Streamlit
        proxy_pass http://streamlit_backend;
        proxy_http_version 1.1;

        # WebSocket support (CRITICAL for Streamlit)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Preserve original domain (FIX for redirect issue)
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port 443;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;

        # Buffering
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
}

# HTTP Server - Port 80 (Redirect to HTTPS with domain preservation)
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    # Server names - DOMAIN FIRST
    server_name mes.pravaig.com;

    # Logging
    access_log /var/log/nginx/battery-mes-redirect.log;

    # Redirect to HTTPS - PRESERVE DOMAIN NAME
    # Use $host to keep original domain, not $server_name
    return 301 https://$host$request_uri;
}

# Catch-all for IP access (redirect to domain)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    # Match IP address only
    server_name 192.168.0.237;

    ssl_certificate /etc/ssl/battery-mes/cert.pem;
    ssl_certificate_key /etc/ssl/battery-mes/key.pem;

    # Redirect IP to domain
    return 301 https://mes.pravaig.com$request_uri;
}

server {
    listen 80;
    listen [::]:80;

    # Match IP address only
    server_name 192.168.0.237;

    # Redirect IP to domain
    return 301 https://mes.pravaig.com$request_uri;
}
NGINX_EOF

echo "✓ Nginx configuration created"

echo ""
echo "=========================================="
echo "Step 6: Enabling site and removing default"
echo "=========================================="
sudo ln -sf /etc/nginx/sites-available/battery-mes /etc/nginx/sites-enabled/battery-mes
sudo rm -f /etc/nginx/sites-enabled/default

echo ""
echo "=========================================="
echo "Step 7: Testing Nginx configuration"
echo "=========================================="
sudo nginx -t

echo ""
echo "=========================================="
echo "Step 8: Configuring firewall"
echo "=========================================="
if command -v ufw &> /dev/null; then
    echo "Configuring UFW firewall..."
    sudo ufw allow 80/tcp comment 'Battery MES HTTP'
    sudo ufw allow 443/tcp comment 'Battery MES HTTPS'

    # Remove old rules
    sudo ufw delete allow 8501/tcp 2>/dev/null || echo "  (no old 8501 rule)"
    sudo ufw delete allow 8443/tcp 2>/dev/null || echo "  (no old 8443 rule)"
    sudo ufw delete allow 8081/tcp 2>/dev/null || echo "  (no old 8081 rule)"

    echo "✓ Firewall configured"
else
    echo "⚠ UFW not installed"
fi

echo ""
echo "=========================================="
echo "Step 9: Starting services"
echo "=========================================="
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

sleep 3

sudo systemctl enable nginx
sudo systemctl start nginx

echo ""
echo "Step 10: Waiting for services..."
sleep 5

echo ""
echo "=========================================="
echo "Step 11: Verifying services"
echo "=========================================="
echo ""
echo "Streamlit Service:"
sudo systemctl status $SERVICE_NAME --no-pager | head -15

echo ""
echo "Nginx Service:"
sudo systemctl status nginx --no-pager | head -15

echo ""
echo "=========================================="
echo "Step 12: Testing endpoints"
echo "=========================================="
echo ""
echo "Testing backend:"
curl -s http://127.0.0.1:8501 > /dev/null && echo "✓ Backend OK" || echo "✗ Backend FAILED"

echo ""
echo "Testing HTTPS (domain):"
curl -skI https://mes.pravaig.com | grep -E "HTTP|Location" || echo "✗ HTTPS FAILED"

echo ""
echo "Testing HTTP redirect:"
curl -sI http://mes.pravaig.com | grep -E "HTTP|Location" || echo "✗ Redirect FAILED"

echo ""
echo "=========================================="
echo "✓ PRODUCTION SSL SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Access URL:"
echo "  Primary: https://mes.pravaig.com"
echo "  HTTP:    http://mes.pravaig.com (→ redirects to HTTPS)"
echo ""
echo "Port Configuration:"
echo "  80  (HTTP)  → Redirects to HTTPS domain"
echo "  443 (HTTPS) → Main application (domain)"
echo "  8501        → Streamlit backend (localhost only)"
echo ""
echo "Features Enabled:"
echo "  ✓ Camera functionality (HTTPS)"
echo "  ✓ WebSocket support"
echo "  ✓ Domain name preservation"
echo "  ✓ IP → Domain redirect"
echo "  ✓ Security headers"
echo "  ✓ HTTP/2 protocol"
echo "  ✓ Session management"
echo ""
echo "SSL Certificate:"
echo "  Type: Self-signed"
echo "  Domain: mes.pravaig.com"
echo "  Valid: 365 days"
echo "  Location: /etc/ssl/battery-mes/"
echo ""
echo "⚠️  Certificate Warning:"
echo "  Users will see 'Not Secure' warning on first visit"
echo "  This is normal for self-signed certificates"
echo "  Click 'Advanced' → 'Proceed to mes.pravaig.com'"
echo ""
echo "Service Management:"
echo "  Status:  sudo systemctl status battery-mes"
echo "  Status:  sudo systemctl status nginx"
echo "  Restart: sudo systemctl restart battery-mes"
echo "  Restart: sudo systemctl restart nginx"
echo "  Logs:    sudo journalctl -u battery-mes -f"
echo "  Logs:    sudo tail -f /var/log/nginx/error.log"
echo ""
echo "Testing:"
echo "  Backend: curl http://127.0.0.1:8501"
echo "  HTTPS:   curl -k https://mes.pravaig.com"
echo "  HTTP:    curl -I http://mes.pravaig.com"
echo ""
echo "Certificate Info:"
echo "  View: openssl x509 -in /etc/ssl/battery-mes/cert.pem -text -noout"
echo "  Verify: openssl verify /etc/ssl/battery-mes/cert.pem"
echo ""
