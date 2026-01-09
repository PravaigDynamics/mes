# DNS Setup Guide for mes.pravaig.com

## Overview
This guide explains how to configure DNS to point `mes.pravaig.com` to your Battery Pack MES server.

## Server Details
- **Domain**: mes.pravaig.com
- **Server IP**: 192.168.0.237
- **Ports**: 80 (HTTP), 443 (HTTPS)

## DNS Configuration

### Option 1: Internal DNS (Local Network)

If you have an internal DNS server (Windows Server DNS, BIND, etc.):

#### Windows Server DNS
1. Open **DNS Manager**
2. Navigate to your domain zone (`pravaig.com`)
3. Right-click → **New Host (A or AAAA)**
4. Enter:
   - **Name**: `mes`
   - **IP Address**: `192.168.0.237`
   - **TTL**: `3600` (1 hour)
5. Click **Add Host**

#### Linux BIND DNS
Edit your zone file (`/etc/bind/zones/pravaig.com.zone`):
```
mes     IN      A       192.168.0.237
```

Then reload:
```bash
sudo systemctl reload named
```

### Option 2: Public DNS (Internet Access)

If mes.pravaig.com should be accessible from the internet:

#### Cloudflare
1. Log into Cloudflare dashboard
2. Select `pravaig.com` domain
3. Go to **DNS** → **Records**
4. Click **Add record**
5. Enter:
   - **Type**: A
   - **Name**: mes
   - **IPv4 address**: 192.168.0.237 (or your public IP)
   - **Proxy status**: DNS only (gray cloud)
   - **TTL**: Auto
6. Click **Save**

#### Route 53 (AWS)
1. Open Route 53 console
2. Select hosted zone for `pravaig.com`
3. Click **Create record**
4. Enter:
   - **Record name**: mes
   - **Record type**: A
   - **Value**: 192.168.0.237
   - **TTL**: 300
5. Click **Create records**

#### Other DNS Providers
Similar steps apply for:
- GoDaddy
- Namecheap
- Google Domains
- Azure DNS

### Option 3: Hosts File (Testing Only)

For local testing without DNS:

**Windows** (`C:\Windows\System32\drivers\etc\hosts`):
```
192.168.0.237    mes.pravaig.com
```

**Linux/Mac** (`/etc/hosts`):
```
192.168.0.237    mes.pravaig.com
```

**Note**: Edit as administrator/root. This only works on the machine where you edit it.

## Verification

### Check DNS Resolution

**Windows:**
```cmd
nslookup mes.pravaig.com
```

**Linux/Mac:**
```bash
dig mes.pravaig.com
# or
nslookup mes.pravaig.com
```

Expected output:
```
Name:    mes.pravaig.com
Address: 192.168.0.237
```

### Test HTTP/HTTPS Access

```bash
# Test HTTP (should redirect to HTTPS)
curl -I http://mes.pravaig.com

# Test HTTPS
curl -k https://mes.pravaig.com
```

## HTTPS Certificate Options

### Option 1: Self-Signed Certificate (Current)
- ✓ Free and immediate
- ✓ Works for internal use
- ✗ Browser security warnings
- ✗ Requires manual acceptance

**Setup**: Already configured by `setup_domain_https.sh`

### Option 2: Let's Encrypt (Recommended)
- ✓ Free and trusted
- ✓ No browser warnings
- ✓ Auto-renewal
- ⚠ Requires public DNS and internet access

**Setup**:
```bash
# Install certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d mes.pravaig.com

# Auto-renewal (already enabled)
sudo systemctl status certbot.timer
```

**Requirements**:
- Domain must be publicly accessible
- Port 80 must be open to internet
- DNS A record must point to public IP

### Option 3: Internal CA Certificate
For enterprise environments with internal Certificate Authority:

1. Generate CSR:
```bash
sudo openssl req -new -newkey rsa:2048 -nodes \
  -keyout /etc/ssl/battery-mes/key.pem \
  -out /etc/ssl/battery-mes/request.csr \
  -subj "/C=IN/ST=Karnataka/L=Bangalore/O=Pravaig Dynamics/CN=mes.pravaig.com"
```

2. Submit CSR to your CA
3. Install signed certificate:
```bash
sudo cp your-signed-cert.pem /etc/ssl/battery-mes/cert.pem
sudo systemctl restart nginx
```

## Network Configuration

### Firewall Rules

Ensure these ports are open:

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw status

# iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

### Router Configuration (if needed)

If accessing from outside your network:

1. **Port Forwarding**:
   - External Port 80 → 192.168.0.237:80
   - External Port 443 → 192.168.0.237:443

2. **NAT Configuration**:
   - Configure NAT rules for the server IP

## Deployment

After DNS is configured, run:

```bash
# SSH to server
ssh giritharan@192.168.0.237

# Navigate to MES directory
cd /home/giritharan/MES

# Make script executable
chmod +x setup_domain_https.sh

# Run setup
./setup_domain_https.sh
```

## Testing Checklist

- [ ] DNS resolves to correct IP
- [ ] HTTP redirects to HTTPS
- [ ] HTTPS loads application
- [ ] QR codes use domain URL
- [ ] Camera functionality works
- [ ] Multiple users can access
- [ ] WebSocket connections work
- [ ] No CORS errors in console

## Troubleshooting

### DNS not resolving
```bash
# Flush DNS cache
# Windows
ipconfig /flushdns

# Linux
sudo systemd-resolve --flush-caches

# Mac
sudo dscacheutil -flushcache
```

### HTTPS not loading
```bash
# Check Nginx status
sudo systemctl status nginx

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Test configuration
sudo nginx -t
```

### Certificate issues
```bash
# Verify certificate
openssl x509 -in /etc/ssl/battery-mes/cert.pem -text -noout

# Check expiry
openssl x509 -in /etc/ssl/battery-mes/cert.pem -enddate -noout
```

## Support

For issues or questions:
- Check logs: `sudo journalctl -u battery-mes -f`
- Nginx logs: `sudo tail -f /var/log/nginx/error.log`
- Test backend: `curl http://127.0.0.1:8501`

## Summary

| Component | Value |
|-----------|-------|
| Domain | mes.pravaig.com |
| Server IP | 192.168.0.237 |
| HTTP Port | 80 (redirects) |
| HTTPS Port | 443 (main) |
| Backend Port | 8501 (internal) |
| Protocol | HTTPS with TLS 1.2/1.3 |
| Certificate | Self-signed (or Let's Encrypt) |

---

**Last Updated**: January 2026
