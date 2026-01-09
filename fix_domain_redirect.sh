#!/bin/bash
# Fix domain redirect issues - Remove all IP-based redirects

set -e

echo "=========================================="
echo "Fixing Domain Redirect Issues"
echo "=========================================="
echo ""

DOMAIN="mes.pravaig.com"
SERVER_IP="192.168.0.237"

echo "Step 1: Stopping Nginx..."
sudo systemctl stop nginx

echo ""
echo "Step 2: Removing old redirect HTML page..."
sudo rm -rf /var/www/battery-mes
echo "✓ Removed old HTML redirect page"

echo ""
echo "Step 3: Backing up current Nginx config..."
sudo cp /etc/nginx/sites-available/battery-mes /tmp/battery-mes.backup.$(date +%s) 2>/dev/null || true

echo ""
echo "Step 4: Installing clean Nginx configuration..."
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

    # IMPORTANT: Domain only, no IP here
    server_name mes.pravaig.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/battery-mes/cert.pem;
    ssl_certificate_key /etc/ssl/battery-mes/key.pem;
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
        proxy_pass http://streamlit_backend;
        proxy_http_version 1.1;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # CRITICAL: Preserve domain name
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

        # Disable buffering
        proxy_buffering off;
        proxy_request_buffering off;
    }
}

# HTTP Server - Port 80 (Redirect to HTTPS)
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    # Domain only
    server_name mes.pravaig.com;

    # Redirect to HTTPS - PRESERVE DOMAIN
    return 301 https://$host$request_uri;
}

# IP Access Handler (redirect to domain)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    # IP only
    server_name 192.168.0.237;

    ssl_certificate /etc/ssl/battery-mes/cert.pem;
    ssl_certificate_key /etc/ssl/battery-mes/key.pem;

    # Redirect to domain
    return 301 https://mes.pravaig.com$request_uri;
}

server {
    listen 80;
    listen [::]:80;

    # IP only
    server_name 192.168.0.237;

    # Redirect to domain
    return 301 https://mes.pravaig.com$request_uri;
}
NGINX_EOF

echo "✓ Clean configuration installed"

echo ""
echo "Step 5: Testing Nginx configuration..."
sudo nginx -t

echo ""
echo "Step 6: Starting Nginx..."
sudo systemctl start nginx

echo ""
echo "Step 7: Testing redirects..."
echo ""
echo "Testing HTTP to HTTPS redirect:"
curl -sI http://mes.pravaig.com | grep -E "HTTP|Location"

echo ""
echo "Testing HTTP IP redirect:"
curl -sI http://192.168.0.237 | grep -E "HTTP|Location"

echo ""
echo "Testing HTTPS IP redirect:"
curl -skI https://192.168.0.237 | grep -E "HTTP|Location"

echo ""
echo "=========================================="
echo "✓ Domain Redirect Fixed!"
echo "=========================================="
echo ""
echo "All redirects now preserve domain name:"
echo "  http://mes.pravaig.com   → https://mes.pravaig.com"
echo "  http://192.168.0.237     → https://mes.pravaig.com"
echo "  https://192.168.0.237    → https://mes.pravaig.com"
echo ""
echo "Clear browser cache:"
echo "  Chrome: Ctrl+Shift+Delete"
echo "  Firefox: Ctrl+Shift+Delete"
echo "  Edge: Ctrl+Shift+Delete"
echo ""
echo "Or use incognito/private mode to test"
echo ""
