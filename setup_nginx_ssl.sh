#!/bin/bash
# Setup Nginx reverse proxy with SSL for Battery Pack MES
# This is the enterprise/production-ready solution

echo "=========================================="
echo "Setting up Nginx with SSL"
echo "=========================================="
echo ""

# Install Nginx
echo "Step 1: Installing Nginx..."
sudo apt update
sudo apt install -y nginx

# Create SSL certificate
echo ""
echo "Step 2: Creating SSL certificate..."
sudo mkdir -p /etc/ssl/battery-mes
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/battery-mes/key.pem \
  -out /etc/ssl/battery-mes/cert.pem \
  -subj "/C=IN/ST=Karnataka/L=Bangalore/O=PDPL/OU=Manufacturing/CN=192.168.0.237"

# Create Nginx config
echo ""
echo "Step 3: Configuring Nginx..."
sudo tee /etc/nginx/sites-available/battery-mes > /dev/null << 'EOF'
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name 192.168.0.237;

    ssl_certificate /etc/ssl/battery-mes/cert.pem;
    ssl_certificate_key /etc/ssl/battery-mes/key.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name 192.168.0.237;
    return 301 https://$server_name$request_uri;
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/battery-mes /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test config
echo ""
echo "Step 4: Testing Nginx configuration..."
sudo nginx -t

# Restart Nginx
echo ""
echo "Step 5: Starting Nginx..."
sudo systemctl restart nginx
sudo systemctl enable nginx

# Configure firewall
echo ""
echo "Step 6: Configuring firewall..."
sudo ufw allow 443/tcp comment 'Battery MES HTTPS'
sudo ufw allow 80/tcp comment 'Battery MES HTTP redirect'

echo ""
echo "=========================================="
echo "Nginx SSL Setup Complete!"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  HTTPS: https://192.168.0.237"
echo "  HTTP:  http://192.168.0.237 (redirects to HTTPS)"
echo ""
echo "Streamlit should be running on localhost:8501"
echo "Nginx will proxy requests with SSL"
echo ""
echo "Status commands:"
echo "  sudo systemctl status nginx"
echo "  sudo systemctl status battery-mes"
echo ""
