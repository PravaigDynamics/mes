# VM Recovery Steps - 192.168.0.237 Unreachable

## Current Status
- ❌ SSH: Connection timed out
- ❌ Ping: Destination host unreachable
- ❌ VM not responding on network

## Possible Causes
1. **VM is powered off** (Most likely)
2. VM's IP address changed (DHCP reassigned)
3. VM's network interface is down
4. VM is on wrong network/VLAN
5. Network cable disconnected (if physical)

---

## Solution 1: Check VM Power Status (Do This First)

### If using VMware/VirtualBox/Hyper-V:
1. Open your virtualization platform
2. Find VM: **PDPLBLRPROD341**
3. Check power status
4. If **Powered Off** → Click **Start/Power On**
5. Wait 2-3 minutes for boot
6. Test: `ping 192.168.0.237`

### If physical server:
1. Go to server location
2. Check if power LED is on
3. Check network cable is connected
4. Press power button if off
5. Wait for boot (2-3 minutes)

---

## Solution 2: Access VM Console Directly

### VMware/VirtualBox/Hyper-V:
1. Open VM console (not SSH, direct console)
2. Login: `giritharan` / `Pdpl@$dec2024`
3. Run these commands:

```bash
# Check IP address
ip addr show

# You should see something like:
# inet 192.168.0.XXX/24

# If IP is different, note the new IP!
```

4. If IP is different than 192.168.0.237:
   - Use the NEW IP for all connections
   - Update config files (I'll help with this)

### Physical server with monitor:
1. Connect keyboard/monitor
2. Login at console
3. Run same commands above

---

## Solution 3: Scan Network to Find VM

Run this command on your Windows machine:

```cmd
# Quick scan for active hosts
for /L %i in (200,1,250) do @ping -n 1 -w 100 192.168.0.%i | find "Reply" && echo Found: 192.168.0.%i
```

For each IP found, try SSH:
```cmd
ssh giritharan@192.168.0.XXX
```

If you get a password prompt, you found it!

---

## Solution 4: Check DHCP Leases

If you have access to your router/DHCP server:
1. Login to router admin panel
2. Go to DHCP leases
3. Look for hostname: **PDPLBLRPROD341**
4. Check assigned IP address

---

## Once VM is Found and Accessible

### Step 1: Set Static IP (Prevent future issues)

```bash
ssh giritharan@[NEW_IP]
# Password: Pdpl@$dec2024

# Check current network interface name
ip addr show

# Edit netplan (Ubuntu)
sudo nano /etc/netplan/00-installer-config.yaml
```

Add/modify:
```yaml
network:
  version: 2
  ethernets:
    ens33:  # Your interface name here
      addresses:
        - 192.168.0.237/24
      gateway4: 192.168.0.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Apply:
```bash
sudo netplan apply
```

### Step 2: Configure Firewall

```bash
cd ~/MES

# Allow port 8501
sudo ufw allow 8501/tcp

# Check firewall status
sudo ufw status
```

### Step 3: Setup Auto-Start Service

```bash
cd ~/MES
./complete_setup.sh
```

### Step 4: Test Access

From your Windows machine:
```cmd
# Test connectivity
ping 192.168.0.237

# Test application
# Open browser: http://192.168.0.237:8501
```

---

## Alternative: Run Locally While Troubleshooting

Run the application on your Windows machine (192.168.0.125) for immediate testing:

1. **Open Command Prompt**
2. **Run:**
   ```cmd
   cd d:\MES
   venv\Scripts\activate
   streamlit run app_unified_db.py
   ```
3. **Access at:** http://192.168.0.125:8501

Other users on your network can access it too!

---

## Quick Troubleshooting Commands

### On VM (via console):
```bash
# Check network status
ip addr show
ip route show

# Check if Streamlit is running
ps aux | grep streamlit

# Start Streamlit manually
cd ~/MES
source venv/bin/activate
streamlit run app_unified_db.py --server.address 0.0.0.0 --server.port 8501
```

### On Windows:
```cmd
# Test connectivity
ping 192.168.0.237

# Test SSH
ssh giritharan@192.168.0.237

# Test HTTP port
telnet 192.168.0.237 8501
# (Ctrl+] then type 'quit' to exit)
```

---

## Contact IT Support (If Needed)

If you can't access the VM yourself, provide IT with:

**VM Information:**
- Hostname: PDPLBLRPROD341
- Expected IP: 192.168.0.237
- OS: Ubuntu Linux
- User: giritharan

**Required Actions:**
1. Verify VM is powered on
2. Check current IP address
3. Configure static IP: 192.168.0.237
4. Open firewall port 8501/tcp
5. Ensure network connectivity to 192.168.0.0/24

**Issue:**
VM not reachable - SSH timeout, ping fails with "Destination host unreachable"

---

## Next Steps Priority

1. ⚡ **URGENT:** Check if VM is powered on
2. 🔍 **If on:** Access console and check IP address
3. 🔧 **If IP changed:** Note new IP and update configs
4. 🚀 **Once accessible:** Run complete_setup.sh
5. ✅ **Test:** http://192.168.0.237:8501

---

**Need Help?**
Let me know what you find and I'll guide you through the next steps!
