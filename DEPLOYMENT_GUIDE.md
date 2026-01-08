# Battery Pack MES - Production Deployment Guide
**VM Deployment with Concurrent User Support**

---

## Overview

This guide will help you deploy the Battery Pack MES application to your VM at **192.168.0.237** with full support for:
- Multiple simultaneous users
- Concurrent data entry and updates
- Last-write-wins conflict resolution
- Automatic database retry on conflicts
- 24/7 availability

---

## Prerequisites

### VM Requirements
- **IP Address:** 192.168.0.237
- **Username:** giritharan
- **Password:** Pdpl@$dec2024
- **OS:** Ubuntu/Debian Linux (recommended) or compatible
- **RAM:** Minimum 2GB, Recommended 4GB+
- **Storage:** 20GB free space

### Local Machine Requirements
- SSH client (Windows 10+ has built-in support)
- OR WinSCP/FileZilla for file transfer

---

## Deployment Steps

### Step 1: Transfer Files to VM

**Option A: Using Windows SCP (Command Line)**
```cmd
# Run the provided batch script
transfer_to_vm.bat

# Or manually:
scp -r D:\MES giritharan@192.168.0.237:/home/giritharan/
```

**Option B: Using WinSCP (GUI)**
1. Download WinSCP: https://winscp.net
2. Create new connection:
   - Host name: 192.168.0.237
   - User name: giritharan
   - Password: Pdpl@$dec2024
3. Connect and transfer `D:\MES` folder to `/home/giritharan/MES`

**Option C: Using FileZilla**
1. Host: sftp://192.168.0.237
2. Username: giritharan
3. Password: Pdpl@$dec2024
4. Port: 22
5. Transfer `D:\MES` to `/home/giritharan/MES`

---

### Step 2: SSH to VM

Open Command Prompt or PowerShell:

```cmd
ssh giritharan@192.168.0.237
# Enter password: Pdpl@$dec2024
```

---

### Step 3: Run Deployment Script

Once connected to the VM:

```bash
# Navigate to application directory
cd ~/MES

# Make deployment script executable
chmod +x deploy_to_vm.sh

# Run deployment (this will take 3-5 minutes)
./deploy_to_vm.sh
```

The deployment script will:
1. Install Python and required system packages
2. Create Python virtual environment
3. Install all dependencies
4. Initialize database with concurrent access support
5. Configure firewall
6. Create systemd service for automatic startup
7. Start the application

---

### Step 4: Verify Deployment

After deployment completes, check the service status:

```bash
# Check if service is running
sudo systemctl status battery-mes

# You should see "active (running)" in green
```

Test local access on VM:
```bash
curl http://localhost:8501
# Should return HTML content
```

---

### Step 5: Test Network Access

From your local machine, open a web browser and navigate to:

```
http://192.168.0.237:8501
```

You should see the Battery Pack MES login screen.

---

## Concurrent Access Features

### Database Enhancements

The application now includes:

1. **WAL Mode (Write-Ahead Logging)**
   - Allows multiple readers and one writer simultaneously
   - Better concurrency than default SQLite

2. **Automatic Retry Logic**
   - Up to 10 retries on database locked errors
   - Exponential backoff (100ms to 2 seconds)
   - Handles race conditions automatically

3. **IMMEDIATE Transactions**
   - Acquires write lock early
   - Reduces chance of conflicts

4. **Increased Timeouts**
   - 30-second database timeout
   - Handles high-concurrency scenarios

### What This Means

- **Multiple users can view data simultaneously** without any conflicts
- **Multiple users can save data at the same time** - the system will queue writes automatically
- **If two users save to the same battery/process simultaneously** - both will succeed, last save wins
- **No "database locked" errors for users** - automatic retry handles it transparently

---

## Testing Concurrent Access

### Test Scenario 1: Multiple Viewers
1. Open browser 1: http://192.168.0.237:8501
2. Open browser 2: http://192.168.0.237:8501
3. Open browser 3: http://192.168.0.237:8501
4. All should load dashboard and data simultaneously ✅

### Test Scenario 2: Concurrent Data Entry
1. Browser 1: Go to "Data Entry" tab
2. Browser 2: Go to "Data Entry" tab
3. Browser 1: Scan Battery Pack "TEST001", enter Cell Sorting data, SAVE
4. Browser 2: Scan Battery Pack "TEST002", enter Cell Sorting data, SAVE
5. Both should save successfully ✅

### Test Scenario 3: Same Battery, Different Process
1. Browser 1: Battery "TEST001" - Cell Sorting - SAVE
2. Browser 2: Battery "TEST001" - Module Assembly - SAVE
3. Both should save successfully ✅

### Test Scenario 4: Same Battery, Same Process (Conflict)
1. Browser 1: Battery "TEST001" - Cell Sorting - Start filling form
2. Browser 2: Battery "TEST001" - Cell Sorting - Start filling form
3. Browser 1: Click SAVE (saves first)
4. Browser 2: Click SAVE (saves second - overwrites first)
5. Both operations succeed, Browser 2's data is final ✅

**This is expected behavior** - last save wins.

### Test Scenario 5: High Concurrency Stress Test
1. Open 5+ browsers
2. All access same battery pack
3. All save data rapidly
4. Check logs: `sudo journalctl -u battery-mes -f`
5. Should see retry messages but all saves succeed ✅

---

## Service Management

### Start/Stop/Restart

```bash
# Start service
sudo systemctl start battery-mes

# Stop service
sudo systemctl stop battery-mes

# Restart service
sudo systemctl restart battery-mes

# Check status
sudo systemctl status battery-mes
```

### View Logs

```bash
# Follow live logs
sudo journalctl -u battery-mes -f

# View last 100 lines
sudo journalctl -u battery-mes -n 100

# View logs for today
sudo journalctl -u battery-mes --since today
```

### Auto-Start on Boot

The service is configured to start automatically on VM reboot.

Test by rebooting:
```bash
sudo reboot
# Wait 2 minutes, then check
sudo systemctl status battery-mes
```

---

## Firewall Configuration

The deployment script automatically opens port 8501. If you need to manually configure:

```bash
# Allow port 8501
sudo ufw allow 8501/tcp

# Check firewall status
sudo ufw status

# Enable firewall if not enabled
sudo ufw enable
```

---

## Backup Configuration

### Manual Backup

```bash
cd ~/MES
python3 -c "from backup_manager import create_backup; create_backup()"
```

### Automatic Daily Backups

Create a cron job:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * cd /home/giritharan/MES && /home/giritharan/MES/venv/bin/python -c "from backup_manager import create_backup; create_backup()" >> /home/giritharan/MES/logs/backup.log 2>&1
```

---

## Monitoring

### Check Database Size

```bash
ls -lh ~/MES/battery_mes.db
```

### Check Disk Space

```bash
df -h
```

### Check Memory Usage

```bash
free -h
```

### Check Service Resource Usage

```bash
# CPU and memory usage
ps aux | grep streamlit

# Or use top
top -p $(pgrep -f streamlit)
```

---

## Troubleshooting

### Issue: Cannot access from network

**Check 1: Service running?**
```bash
sudo systemctl status battery-mes
```

**Check 2: Firewall open?**
```bash
sudo ufw status
# Should show 8501/tcp ALLOW
```

**Check 3: Listening on correct interface?**
```bash
sudo netstat -tulpn | grep 8501
# Should show 0.0.0.0:8501 (not 127.0.0.1:8501)
```

**Fix:**
```bash
# Restart service
sudo systemctl restart battery-mes

# Check config
cat ~/MES/.streamlit/config.toml
# Verify: address = "0.0.0.0"
```

### Issue: Database locked errors

**This should NOT happen with the new retry logic, but if it does:**

```bash
# Check for multiple instances
ps aux | grep streamlit
# Should see only ONE streamlit process

# Kill zombie processes
pkill -f streamlit

# Restart service
sudo systemctl restart battery-mes
```

### Issue: Service won't start

**Check logs:**
```bash
sudo journalctl -u battery-mes -n 50
```

**Common causes:**
- Port 8501 already in use
- Python dependency missing
- Database file permissions

**Fix:**
```bash
# Check port
sudo lsof -i :8501

# Re-install dependencies
cd ~/MES
source venv/bin/activate
pip install -r requirements_new.txt

# Fix permissions
chmod 644 ~/MES/battery_mes.db
```

### Issue: Slow performance with many users

**Optimize database:**
```bash
cd ~/MES
sqlite3 battery_mes.db "VACUUM; ANALYZE;"
```

**Check logs for errors:**
```bash
sudo journalctl -u battery-mes --since "10 minutes ago"
```

### Issue: Need to update application

```bash
# Stop service
sudo systemctl stop battery-mes

# Backup current files
cp -r ~/MES ~/MES.backup.$(date +%Y%m%d)

# Transfer new files from local machine
# Then restart
sudo systemctl restart battery-mes
```

---

## Performance Optimization

### For Heavy Concurrent Use (10+ users)

1. **Increase VM RAM** to 8GB+
2. **Use PostgreSQL instead of SQLite:**
   ```bash
   # Install PostgreSQL
   sudo apt install postgresql postgresql-contrib

   # Set DATABASE_URL environment variable
   # In service file: Environment="DATABASE_URL=postgresql://..."
   ```

3. **Monitor and tune:**
   ```bash
   # Watch performance
   watch -n 1 "ps aux | grep streamlit"
   ```

---

## Security Recommendations

### 1. Restrict Access to Local Network

```bash
# Only allow access from 192.168.0.0/24 network
sudo ufw delete allow 8501/tcp
sudo ufw allow from 192.168.0.0/24 to any port 8501 proto tcp
```

### 2. Change Default Password

Update your VM user password:
```bash
passwd
```

### 3. Enable SSH Key Authentication

(Optional but recommended for security)

---

## User Access Instructions

Share this with your team:

**Access URL:**
```
http://192.168.0.237:8501
```

**Workflow:**
1. Open browser, go to URL above
2. Go to "Data Entry" tab
3. Scan or enter Battery Pack ID
4. Select process and fill QC checks
5. Click "Save Production Data"
6. View progress in "Dashboard" tab
7. Download reports from "Reports" tab

**Multiple Users:**
- Everyone can use the system at the same time
- Data saves automatically handle conflicts
- Dashboard refreshes to show latest data
- Download your own reports anytime

---

## Success Criteria

After deployment, verify:

- [ ] Service is running: `sudo systemctl status battery-mes`
- [ ] Accessible from network: http://192.168.0.237:8501
- [ ] Can create QR codes
- [ ] Can enter data for different battery packs (3+ users)
- [ ] Can enter data for same battery pack (2+ users)
- [ ] Dashboard updates with new data
- [ ] Can download reports
- [ ] Service survives VM reboot
- [ ] Logs show no critical errors
- [ ] Database backups are working

---

## Support

If you encounter issues:

1. **Check logs:** `sudo journalctl -u battery-mes -f`
2. **Check service:** `sudo systemctl status battery-mes`
3. **Check network:** `curl http://localhost:8501`
4. **Restart service:** `sudo systemctl restart battery-mes`

For persistent issues, collect:
- Service status: `sudo systemctl status battery-mes`
- Recent logs: `sudo journalctl -u battery-mes -n 100`
- System info: `df -h && free -h`

---

## Quick Reference Commands

| Task | Command |
|------|---------|
| Check status | `sudo systemctl status battery-mes` |
| Start | `sudo systemctl start battery-mes` |
| Stop | `sudo systemctl stop battery-mes` |
| Restart | `sudo systemctl restart battery-mes` |
| View logs | `sudo journalctl -u battery-mes -f` |
| Access URL | http://192.168.0.237:8501 |
| SSH to VM | `ssh giritharan@192.168.0.237` |
| Backup database | `python3 -c "from backup_manager import create_backup; create_backup()"` |

---

## Next Steps After Deployment

1. **Test thoroughly** with multiple users
2. **Set up automatic backups** (cron job)
3. **Monitor logs** for first few days
4. **Train users** on the workflow
5. **Create desktop shortcuts** on production floor PCs
6. **Document any issues** and solutions

---

**Deployment Date:** _________
**Deployed By:** _________
**VM IP:** 192.168.0.237
**Access URL:** http://192.168.0.237:8501

---

Good luck with your deployment! 🚀
