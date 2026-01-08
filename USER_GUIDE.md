# Battery Pack MES - User Guide
**Quick Start Guide for Production Floor**

---

## 🔍 How to Scan QR Codes (Camera Not Available on HTTP)

Since the application runs on HTTP (http://192.168.0.237:8501), live camera scanning is not available due to browser security.

**Use the Photo Upload Method Instead:**

### Method 1: Upload Photo (Recommended)

1. **Take a photo** of the battery pack QR code
   - Use your phone camera OR
   - Use a desktop camera/webcam and save the photo

2. **Open the application:** http://192.168.0.237:8501

3. **Go to "Data Entry" tab**

4. **Click "Upload QR Code Photo"** button

5. **Select the photo** from your device

6. **Battery ID detected automatically!** ✅

7. Continue with data entry

---

### Method 2: Manual Entry (Backup)

If you don't have a photo:

1. **Manually type** the Battery Pack ID

2. **Click "Set ID"**

3. Continue with data entry

---

## 📱 Recommended Setup for Production Floor

### Option A: Dedicated PC with Camera
1. PC connected to camera/webcam
2. Capture photo of QR code
3. Upload to application
4. Enter data

### Option B: Phone + PC Workflow
1. Scan QR with phone camera
2. Transfer photo to PC (USB cable, network share, or email)
3. Upload to application
4. Enter data

### Option C: Manual Entry
1. Read Battery Pack ID from label
2. Type into application
3. Enter data

---

## 🔐 Why Camera Doesn't Work Directly?

Modern browsers (Chrome, Firefox, Edge) require **HTTPS** (secure connection) for camera access.

Your application runs on **HTTP** for simplicity and speed.

**Solutions:**
- ✅ Use Photo Upload (current, works perfectly)
- ⚠️ Ask IT to enable HTTPS (requires SSL certificate setup)

---

## 📊 Complete Workflow

### Step 1: Access Application
- Open browser
- Go to: http://192.168.0.237:8501
- You'll see the main screen

### Step 2: Identify Battery Pack
- **Option A:** Upload QR photo → Battery ID detected
- **Option B:** Type Battery ID manually

### Step 3: Select Process
- Choose the process (Cell Sorting, Module Assembly, etc.)
- Select your name as Technician
- Add QC Inspector name (optional)

### Step 4: Fill QC Checks
- Answer each quality check
- Mark as "OK", "NOT OK", or "N/A"
- For Module X and Module Y

### Step 5: Add Remarks
- Add any notes or observations (optional)

### Step 6: Save
- Click "Save Production Data"
- ✅ Data saved successfully!
- Scan next battery pack

### Step 7: View Dashboard
- Go to "Dashboard" tab
- See all batteries in progress
- Check production status

### Step 8: Download Reports
- Go to "Reports" tab
- Download Excel files
- Download complete database

---

## 🆘 Common Issues

### "Cannot access camera"
➡️ **Solution:** Use "Upload QR Code Photo" instead

### "Connection timeout"
➡️ **Solution:** Check if VM is powered on and network is connected

### "Database locked"
➡️ **Solution:** Application handles this automatically (retry logic)
➡️ Just wait 2-3 seconds and try again

### "QR Code not detected"
➡️ **Solution:**
- Ensure photo is clear and well-lit
- QR code should be centered
- Try taking photo again

---

## 👥 Multiple Users

✅ **Multiple users CAN work simultaneously!**

- Everyone can view dashboards at the same time
- Everyone can enter data for different batteries
- If two people enter data for the same battery + process:
  - Both will succeed
  - **Last save wins** (this is expected)

---

## 📞 Support

**Application URL:** http://192.168.0.237:8501

**IT Support:** Contact your system administrator

**For Technical Issues:** Check VM status and application logs

---

## 🎯 Tips for Best Results

1. **Clear photos:** Take clear, well-lit photos of QR codes
2. **Check twice:** Verify Battery ID before saving
3. **Save often:** Data is saved immediately to database
4. **Use Dashboard:** Monitor production progress in real-time
5. **Download reports:** Download Excel reports regularly for backup

---

**Need HTTPS/Camera Access?**
Contact IT to set up SSL certificate for camera-based scanning.
