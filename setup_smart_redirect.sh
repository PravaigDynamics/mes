#!/bin/bash
# Smart HTTP/HTTPS redirect with automatic fallback
# If HTTPS fails, HTTP works as backup

set -e

echo "=========================================="
echo "Smart HTTP/HTTPS Redirect Setup"
echo "=========================================="
echo ""
echo "This configures:"
echo "  • Port 80 (HTTP): Smart redirect page"
echo "  • Port 8080 (HTTP): Direct Streamlit access"
echo "  • Port 8443 (HTTPS): Secure Streamlit access"
echo ""
echo "Behavior:"
echo "  1. User visits 192.168.0.237"
echo "  2. Tries HTTPS first (for camera)"
echo "  3. Auto-falls back to HTTP if HTTPS fails"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

SERVER_IP="192.168.0.237"
APP_DIR="/home/giritharan/MES"

# Create redirect HTML page
echo ""
echo "Step 1: Creating smart redirect page..."
sudo mkdir -p /var/www/battery-mes
sudo tee /var/www/battery-mes/index.html > /dev/null << 'HTML_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Battery Pack MES - Redirecting...</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        .spinner {
            border: 5px solid #f3f3f3;
            border-top: 5px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .message {
            font-size: 18px;
            margin-top: 20px;
        }
        .manual-links {
            margin-top: 30px;
            font-size: 14px;
        }
        .manual-links a {
            color: #ffd700;
            text-decoration: none;
            margin: 0 10px;
        }
        .manual-links a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Battery Pack MES</h1>
        <div class="spinner"></div>
        <div class="message" id="message">Connecting to secure server...</div>
        <div class="manual-links">
            <p>Manual access:</p>
            <a href="https://192.168.0.237:8443" id="httpsLink">HTTPS (Secure - Camera enabled)</a>
            <a href="http://192.168.0.237:8080" id="httpLink">HTTP (Fallback)</a>
        </div>
    </div>

    <script>
        // Try HTTPS first, fall back to HTTP if it fails
        const httpsUrl = 'https://192.168.0.237:8443';
        const httpUrl = 'http://192.168.0.237:8080';
        const messageEl = document.getElementById('message');

        // Test HTTPS availability
        function testHttps() {
            return new Promise((resolve, reject) => {
                const img = new Image();
                const timeout = setTimeout(() => {
                    reject('timeout');
                }, 3000); // 3 second timeout

                img.onload = () => {
                    clearTimeout(timeout);
                    resolve(true);
                };
                img.onerror = () => {
                    clearTimeout(timeout);
                    reject('error');
                };

                // Try to load a resource from HTTPS endpoint
                img.src = httpsUrl + '/favicon.png?' + new Date().getTime();
            });
        }

        // Redirect logic
        async function smartRedirect() {
            try {
                messageEl.textContent = 'Testing secure connection...';
                await testHttps();
                messageEl.textContent = 'Redirecting to HTTPS (secure)...';
                setTimeout(() => {
                    window.location.href = httpsUrl;
                }, 500);
            } catch (error) {
                messageEl.textContent = 'HTTPS unavailable, using HTTP fallback...';
                setTimeout(() => {
                    window.location.href = httpUrl;
                }, 1000);
            }
        }

        // Start redirect after page loads
        window.onload = () => {
            setTimeout(smartRedirect, 500);
        };
    </script>
</body>
</html>
HTML_EOF

echo "✓ Smart redirect page created"

echo ""
echo "Step 2: Updating Nginx configuration..."
sudo tee /etc/nginx/sites-available/battery-mes > /dev/null << 'NGINX_EOF'
# HTTP Server - Port 80 (Smart redirect page)
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name 192.168.0.237;

    root /var/www/battery-mes;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}

# HTTP Fallback - Port 8080 (Direct Streamlit access)
server {
    listen 8080;
    listen [::]:8080;
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

# HTTPS Server - Port 8443 (Secure Streamlit access)
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

echo "✓ Nginx configuration updated"

echo ""
echo "Step 3: Updating firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp comment 'Battery MES Smart Redirect'
    sudo ufw allow 8080/tcp comment 'Battery MES HTTP Fallback'
    sudo ufw allow 8443/tcp comment 'Battery MES HTTPS'
    echo "✓ Firewall rules updated"
fi

echo ""
echo "Step 4: Testing Nginx configuration..."
sudo nginx -t

echo ""
echo "Step 5: Restarting Nginx..."
sudo systemctl restart nginx

echo ""
echo "=========================================="
echo "✓ Smart Redirect Setup Complete!"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  Primary: http://192.168.0.237 or just 192.168.0.237"
echo "           → Automatically tries HTTPS first"
echo "           → Falls back to HTTP if HTTPS fails"
echo ""
echo "  Direct HTTPS: https://192.168.0.237:8443 (Camera enabled)"
echo "  Direct HTTP:  http://192.168.0.237:8080 (Fallback)"
echo ""
echo "How it works:"
echo "  1. User visits 192.168.0.237"
echo "  2. Smart page tests HTTPS availability"
echo "  3. If HTTPS works → Redirects to port 8443 (secure)"
echo "  4. If HTTPS fails → Redirects to port 8080 (fallback)"
echo ""
echo "Testing:"
echo "  curl http://192.168.0.237"
echo "  (Should return HTML redirect page)"
echo ""
