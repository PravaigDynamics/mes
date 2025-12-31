# VM SERVER DEPLOYMENT GUIDE
**Battery Pack MES v2.2 - Complete Deployment Instructions**

---

## ✅ **YOUR SETUP: PERFECT CHOICE!**

Your own VM server is the **BEST option** because:
- ✅ Complete data control
- ✅ Database persists forever
- ✅ All features work 100%
- ✅ Local network access
- ✅ No monthly costs
- ✅ Professional setup

---

## 📋 **PRE-DEPLOYMENT CHECKLIST**

### 1. **VM Server Requirements**

**Minimum Specs:**
- OS: Ubuntu 20.04+ / Windows Server 2019+ / CentOS 7+
- CPU: 2 cores
- RAM: 4GB
- Disk: 20GB free space
- Network: Static IP on local network

**Recommended Specs:**
- CPU: 4 cores
- RAM: 8GB
- Disk: 50GB
- Network: Gigabit connection

### 2. **Software Requirements**

**For Ubuntu/Linux:**
```bash
sudo apt update
sudo apt install -y python3.9 python3-pip python3-venv git
```

**For Windows Server:**
- Download Python 3.9+: https://www.python.org/downloads/
- Check "Add Python to PATH" during installation

### 3. **Network Configuration**

**Get VM's IP Address:**

Linux:
```bash
ip addr show
# OR
hostname -I
```

Windows:
```cmd
ipconfig
```

**Example IP**: `192.168.1.100`

---

## 🚀 **DEPLOYMENT STEPS**

### **STEP 1: Upload Files to VM**

**Option A: Using Git (Recommended)**
```bash
cd /opt  # Linux
# OR
cd C:\  # Windows

git clone <your-repository-url> MES
cd MES
```

**Option B: Using SCP/FTP**
```bash
# From your local PC
scp -r D:\MES username@192.168.1.100:/opt/MES
```

**Option C: Manual Copy**
- Copy entire `D:\MES` folder to VM
- Use WinSCP (Windows) or FileZilla

---

### **STEP 2: Install Dependencies**

**On Ubuntu/Linux:**
```bash
cd /opt/MES

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements_new.txt
```

**On Windows Server:**
```cmd
cd C:\MES

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate.bat

# Install dependencies
pip install --upgrade pip
pip install -r requirements_new.txt
```

---

### **STEP 3: Configure Firewall**

**Ubuntu/Linux:**
```bash
# Allow port 8501
sudo ufw allow 8501/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

**Windows Server:**
```powershell
# Open PowerShell as Administrator
New-NetFirewallRule -DisplayName "Battery MES" -Direction Inbound -LocalPort 8501 -Protocol TCP -Action Allow
```

---

### **STEP 4: Create Systemd Service (Linux)**

**Create service file:**
```bash
sudo nano /etc/systemd/system/battery-mes.service
```

**Paste this configuration:**
```ini
[Unit]
Description=Battery Pack MES Application
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/MES
Environment="PATH=/opt/MES/venv/bin"
ExecStart=/opt/MES/venv/bin/streamlit run app_unified_db.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable battery-mes
sudo systemctl start battery-mes

# Check status
sudo systemctl status battery-mes
```

---

### **STEP 5: Create Windows Service (Windows Server)**

**Option A: Using NSSM (Non-Sucking Service Manager)**

Download NSSM: https://nssm.cc/download

```cmd
# Install NSSM
nssm install BatteryMES

# Configure:
Path: C:\MES\venv\Scripts\streamlit.exe
Startup directory: C:\MES
Arguments: run app_unified_db.py --server.port 8501 --server.address 0.0.0.0 --server.headless true

# Start service
nssm start BatteryMES
```

**Option B: Manual Startup Script**

Create `C:\MES\start_server.bat`:
```batch
@echo off
title Battery Pack MES Server
cd /d C:\MES
call venv\Scripts\activate.bat
streamlit run app_unified_db.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

Add to Windows Task Scheduler to run on startup.

---

### **STEP 6: Verify Deployment**

**Check if service is running:**

Linux:
```bash
sudo systemctl status battery-mes
# OR
ps aux | grep streamlit
```

Windows:
```cmd
tasklist | findstr streamlit
```

**Test access:**

From VM itself:
```bash
curl http://localhost:8501
```

From another PC:
```
http://192.168.1.100:8501
```

---

## 🔒 **SECURITY CONFIGURATION**

### 1. **Restrict Access to Local Network**

**Linux (iptables):**
```bash
# Allow only local network (e.g., 192.168.1.0/24)
sudo iptables -A INPUT -p tcp --dport 8501 -s 192.168.1.0/24 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8501 -j DROP

# Save rules
sudo netfilter-persistent save
```

**Windows Firewall:**
```powershell
# Restrict to local subnet
Set-NetFirewallRule -DisplayName "Battery MES" -RemoteAddress 192.168.1.0/24
```

### 2. **Create Streamlit Config**

Create `.streamlit/config.toml`:
```toml
[server]
port = 8501
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
serverAddress = "192.168.1.100"
serverPort = 8501
```

---

## 💾 **BACKUP CONFIGURATION**

### **Automated Daily Backups**

**Linux (cron job):**
```bash
# Create backup script
nano /opt/MES/backup_database.sh
```

**Paste:**
```bash
#!/bin/bash
BACKUP_DIR="/opt/MES/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp /opt/MES/battery_mes.db "$BACKUP_DIR/battery_mes_backup_$TIMESTAMP.db"

# Keep only last 30 backups
cd $BACKUP_DIR
ls -t battery_mes_backup_*.db | tail -n +31 | xargs -r rm

echo "Backup completed: $TIMESTAMP"
```

**Make executable:**
```bash
chmod +x /opt/MES/backup_database.sh
```

**Add to crontab:**
```bash
crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * /opt/MES/backup_database.sh >> /var/log/mes-backup.log 2>&1
```

**Windows (Task Scheduler):**

Create `C:\MES\backup_database.bat`:
```batch
@echo off
set BACKUP_DIR=C:\MES\backups
set TIMESTAMP=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

copy "C:\MES\battery_mes.db" "%BACKUP_DIR%\battery_mes_backup_%TIMESTAMP%.db"

echo Backup completed: %TIMESTAMP%
```

Add to Task Scheduler (daily at 2 AM).

---

## 📊 **MONITORING & MAINTENANCE**

### **Check Logs**

**Linux:**
```bash
# Application logs
sudo journalctl -u battery-mes -f

# Streamlit logs
tail -f ~/.streamlit/logs/*
```

**Windows:**
```cmd
# Check service logs
sc query BatteryMES

# Application logs
type C:\Users\<username>\.streamlit\logs\*.log
```

### **Restart Service**

**Linux:**
```bash
sudo systemctl restart battery-mes
```

**Windows:**
```cmd
nssm restart BatteryMES
```

### **Update Application**

```bash
cd /opt/MES
git pull  # If using git

# Restart service
sudo systemctl restart battery-mes  # Linux
nssm restart BatteryMES  # Windows
```

---

## 🌐 **ACCESS INSTRUCTIONS FOR USERS**

### **From Production Floor PCs**

**URL to Access:**
```
http://192.168.1.100:8501
```

**Create Desktop Shortcut:**

Windows:
- Right-click Desktop → New → Shortcut
- Location: `http://192.168.1.100:8501`
- Name: `Battery Pack MES`

Linux:
Create `~/Desktop/battery-mes.desktop`:
```ini
[Desktop Entry]
Name=Battery Pack MES
Type=Link
URL=http://192.168.1.100:8501
Icon=applications-internet
```

### **Recommended Browsers**
- Chrome (Recommended)
- Edge
- Firefox

---

## ✅ **POST-DEPLOYMENT TESTING**

### **Test Checklist:**

- [ ] Access from VM: http://localhost:8501
- [ ] Access from PC1: http://192.168.1.100:8501
- [ ] Access from PC2: http://192.168.1.100:8501
- [ ] Enter test data
- [ ] Complete a process
- [ ] Download Excel file
- [ ] Generate QR code
- [ ] View dashboard
- [ ] Download CSV report
- [ ] Test concurrent access (2+ users)
- [ ] Verify database backup created
- [ ] Test service restart
- [ ] Test server reboot

---

## 🆘 **TROUBLESHOOTING**

### **Issue: Cannot access from other PCs**

**Check:**
1. Firewall allows port 8501
2. Service is running
3. Using correct IP address
4. PCs on same network

**Fix:**
```bash
# Check if port is listening
netstat -tuln | grep 8501  # Linux
netstat -an | findstr :8501  # Windows
```

### **Issue: Service won't start**

**Check logs:**
```bash
sudo journalctl -u battery-mes -n 50  # Linux
```

**Common causes:**
- Port 8501 already in use
- Python venv not activated
- Missing dependencies
- Wrong file paths

### **Issue: Database locked error**

**Fix:**
```bash
# Check for zombie processes
ps aux | grep streamlit
kill <PID>

# Restart service
sudo systemctl restart battery-mes
```

---

## 📱 **OPTIONAL: HTTPS/SSL SETUP**

For secure access (HTTPS), use nginx reverse proxy:

**Install nginx:**
```bash
sudo apt install nginx certbot python3-certbot-nginx
```

**Configure nginx:**
```nginx
server {
    listen 443 ssl;
    server_name mes.yourcompany.local;

    ssl_certificate /etc/ssl/certs/mes.crt;
    ssl_certificate_key /etc/ssl/private/mes.key;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## 📋 **QUICK REFERENCE COMMANDS**

| Task | Linux Command | Windows Command |
|------|--------------|----------------|
| Start service | `sudo systemctl start battery-mes` | `nssm start BatteryMES` |
| Stop service | `sudo systemctl stop battery-mes` | `nssm stop BatteryMES` |
| Restart service | `sudo systemctl restart battery-mes` | `nssm restart BatteryMES` |
| Check status | `sudo systemctl status battery-mes` | `sc query BatteryMES` |
| View logs | `sudo journalctl -u battery-mes -f` | `type %USERPROFILE%\.streamlit\logs\*.log` |
| Manual backup | `/opt/MES/backup_database.sh` | `C:\MES\backup_database.bat` |

---

## 🎓 **USER TRAINING GUIDE**

Create and share with users:

**Access URL:** `http://192.168.1.100:8501`

**Basic Workflow:**
1. Go to "Data Entry" tab
2. Scan QR code or enter Battery Pack ID
3. Select process
4. Fill in technician name and QC checks
5. Click "Save Production Data"
6. When ready, select process again and click "Complete Process"

**Viewing Reports:**
1. Go to "Dashboard" tab - See all battery packs progress
2. Go to "Reports" tab - Download individual Excel files

---

## ✅ **DEPLOYMENT COMPLETE!**

Your Battery Pack MES is now:
- ✅ Running 24/7 on your VM
- ✅ Accessible from all factory PCs
- ✅ Automatically backing up daily
- ✅ Starting automatically on VM reboot
- ✅ Ready for production use

**Support Contact:** [Your email/phone]
**Server IP:** 192.168.1.100:8501
**Admin Access:** SSH to VM server
