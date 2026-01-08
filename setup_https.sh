#!/bin/bash
# Setup HTTPS for Battery Pack MES using self-signed certificate
# Run this on the VM to enable camera access

echo "=========================================="
echo "Setting up HTTPS for Battery Pack MES"
echo "=========================================="
echo ""

cd ~/MES

# Create SSL directory
mkdir -p ssl
cd ssl

echo "Step 1: Generating self-signed SSL certificate..."
echo ""

# Generate self-signed certificate (valid for 1 year)
openssl req -x509 -newkey rsa:4096 -nodes \
  -out cert.pem \
  -keyout key.pem \
  -days 365 \
  -subj "/C=IN/ST=Karnataka/L=Bangalore/O=PDPL/OU=Manufacturing/CN=192.168.0.237"

echo ""
echo "Step 2: Creating HTTPS startup script..."
cd ~/MES

cat > start_https.sh << 'EOF'
#!/bin/bash
cd ~/MES
source venv/bin/activate

# Start Streamlit with HTTPS
streamlit run app_unified_db.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.sslCertFile ssl/cert.pem \
  --server.sslKeyFile ssl/key.pem
EOF

chmod +x start_https.sh

echo ""
echo "=========================================="
echo "HTTPS Setup Complete!"
echo "=========================================="
echo ""
echo "To start with HTTPS:"
echo "  ./start_https.sh"
echo ""
echo "Access URL: https://192.168.0.237:8501"
echo ""
echo "⚠️  IMPORTANT: Self-signed certificate warning"
echo "Users will see a security warning in browser."
echo "They need to click 'Advanced' → 'Proceed to 192.168.0.237'"
echo ""
echo "For production, use a proper certificate from Let's Encrypt"
echo ""
