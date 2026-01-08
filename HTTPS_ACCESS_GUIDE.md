# HTTPS Access Guide - Battery Pack MES

## ✅ HTTPS is Now Enabled!

Your application is now running with HTTPS (secure connection) and **live camera scanning is enabled!**

---

## 🌐 New Access URL

**Old URL (HTTP):** ~~http://192.168.0.237:8501~~
**New URL (HTTPS):** **https://192.168.0.237:8501**

⚠️ **Important:** Make sure to use **https://** (not http://)

---

## 🔐 Certificate Warning (First Time Access)

Because we're using a self-signed SSL certificate, browsers will show a security warning the **first time** you access the site.

### Chrome

1. You'll see: **"Your connection is not private"**
2. Click **"Advanced"**
3. Click **"Proceed to 192.168.0.237 (unsafe)"**
4. Done! ✅

### Firefox

1. You'll see: **"Warning: Potential Security Risk Ahead"**
2. Click **"Advanced..."**
3. Click **"Accept the Risk and Continue"**
4. Done! ✅

### Edge

1. You'll see: **"Your connection isn't private"**
2. Click **"Advanced"**
3. Click **"Continue to 192.168.0.237 (unsafe)"**
4. Done! ✅

**Note:** After accepting once, you won't see this warning again on that browser/computer.

---

## 📷 Camera Access (Now Available!)

With HTTPS enabled, the **live camera QR code scanner** now works!

### How to Use Live Camera:

1. Open: **https://192.168.0.237:8501**
2. Go to **"Data Entry"** tab
3. Click **"Open Camera Scanner"** button
4. Browser will ask: **"Allow camera access?"**
5. Click **"Allow"** ✅
6. Point camera at QR code
7. Battery ID detected automatically!

### Two Scanning Methods Now Available:

| Method | When to Use |
|--------|-------------|
| **📷 Live Camera** | Desktop/laptop with webcam, quick scanning |
| **📁 Photo Upload** | Mobile photos, saved images, any device |

Both work perfectly! Choose what's convenient for you.

---

## 🔄 What Changed?

| Feature | Before (HTTP) | After (HTTPS) |
|---------|--------------|---------------|
| **URL** | http://192.168.0.237:8501 | https://192.168.0.237:8501 |
| **Security** | Not encrypted | Encrypted (SSL) |
| **Live Camera** | ❌ Not allowed by browser | ✅ Works! |
| **Photo Upload** | ✅ Works | ✅ Still works |
| **All Features** | ✅ Works | ✅ Works |

---

## 🖥️ Server Information

**SSL Certificate Location:** `/home/giritharan/MES/ssl/`
- Certificate: `cert.pem`
- Private Key: `key.pem`

**Certificate Validity:** 1 year (expires January 2027)

**Log File:** `/home/giritharan/MES/streamlit_https.log`

---

## 🔧 Management Commands

### Check if HTTPS app is running:
```bash
ssh giritharan@192.168.0.237
ps aux | grep streamlit
```

### View logs:
```bash
ssh giritharan@192.168.0.237
tail -f ~/MES/streamlit_https.log
```

### Restart HTTPS application:
```bash
ssh giritharan@192.168.0.237
killall streamlit
cd ~/MES
./start_https.sh
```

### Start on boot (systemd service):
```bash
ssh giritharan@192.168.0.237
cd ~/MES
sudo ./complete_setup.sh
# When asked, update the ExecStart line to use start_https.sh
```

---

## 📱 Share with Your Team

**Tell your team:**

1. **New URL:** https://192.168.0.237:8501 (note the 's' in https)
2. **First access:** Accept the security warning (one-time only)
3. **Camera now works:** Click "Allow" when browser asks for camera permission
4. **Everything else same:** All features work exactly as before

---

## ⚠️ Why "Not Secure" Warning?

The warning appears because we're using a **self-signed certificate** (we created it ourselves) instead of a certificate from a trusted authority.

**This is completely safe for internal use!** The connection is still encrypted.

**To remove warning (optional):**
1. Get a domain name (e.g., mes.yourcompany.com)
2. Use Let's Encrypt free SSL certificate
3. Or purchase commercial SSL certificate

For internal factory network use, the self-signed certificate is perfectly fine.

---

## ✅ What's Working Now

- ✅ HTTPS encryption
- ✅ Live camera QR scanning
- ✅ Photo upload QR scanning
- ✅ All data entry features
- ✅ Dashboard and reports
- ✅ Multi-user concurrent access
- ✅ Database with retry logic
- ✅ Automatic backup system

---

## 🎯 Quick Start for Users

1. **Open browser**
2. **Go to:** https://192.168.0.237:8501
3. **Accept security warning** (one-time)
4. **Try live camera:**
   - Go to "Data Entry" tab
   - Click "Open Camera Scanner"
   - Allow camera access
   - Scan QR code!

---

## 📞 Support

**Issues with certificate warning?**
- Just click "Advanced" → "Proceed to site"
- This is normal with self-signed certificates

**Camera not working?**
- Make sure you're using **https://** (not http://)
- Click "Allow" when browser asks for camera permission
- Check if camera is working in other apps

**Other issues?**
- Check VM is running
- Verify HTTPS app is running: `ps aux | grep streamlit`
- Check logs: `tail ~/MES/streamlit_https.log`

---

**Deployment Date:** January 8, 2026
**Access URL:** https://192.168.0.237:8501
**Certificate Expiry:** January 2027

---

🎉 **Enjoy live camera QR scanning!**
