#!/bin/bash
# Update Nginx to redirect HTTP to HTTPS by default

set -e

echo "=========================================="
echo "Update Nginx - Add HTTP to HTTPS Redirect"
echo "=========================================="
echo ""

SERVER_IP="192.168.0.237"

echo "Updating Nginx configuration..."
echo "HTTP (port 80) will redirect to HTTPS (port 8443)"
echo ""

sudo tee /etc/nginx/sites-available/battery-mes > /dev/null << 'NGINX_EOF'
# HTTP Server - Port 80 (Redirects to HTTPS)
server {
    listen 80;
    listen [::]:80;
    server_name 192.168.0.237;

    # Redirect all HTTP traffic to HTTPS
    return 301 https://$host:8443$request_uri;
}

# HTTPS Server - Port 8443 (Main application)
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
NGINX_EOF

echo "✓ Nginx configuration updated"

echo ""
echo "Testing Nginx configuration..."
sudo nginx -t

echo ""
echo "Restarting Nginx..."
sudo systemctl restart nginx

echo ""
echo "=========================================="
echo "✓ Update Complete!"
echo "=========================================="
echo ""
echo "New Behavior:"
echo "  • Type '192.168.0.237' → Auto-redirects to HTTPS (8443)"
echo "  • Type 'http://192.168.0.237' → Redirects to HTTPS (8443)"
echo "  • Type 'https://192.168.0.237:8443' → Direct HTTPS access"
echo ""
echo "Manual HTTP Fallback (if HTTPS fails):"
echo "  • Stop Nginx:  sudo systemctl stop nginx"
echo "  • Access via:  http://192.168.0.237:8501 (direct Streamlit)"
echo ""
echo "Testing:"
echo "  curl -I http://192.168.0.237"
echo "  (Should show: HTTP/1.1 301 Moved Permanently)"
echo ""
