# QR Code Download Guide

## Overview

The QR Generator tab now includes a download section for all saved QR codes, matching the format of the Reports page.

---

## What Changed

**Before:**
- Only generate new QR codes
- No way to access previously generated codes
- Had to manually browse qr_codes folder

**Now:**
- Two tabs: Generate New + Saved QR Codes
- List view of all saved QR codes
- Individual download buttons
- Search and sort functionality
- Bulk download as ZIP
- Same format as Reports page

---

## Using the QR Generator

### Tab 1: Generate New QR Code

1. Enter Battery Pack ID
2. Select QR Code Size (200-500 px)
3. Enable/disable text label
4. Click "Generate QR Code"
5. QR code is created and saved automatically
6. Download immediately or access later from Saved QR Codes tab

**Note:** All generated QR codes are automatically saved to qr_codes/ folder.

---

### Tab 2: Saved QR Codes

**Layout:**
- Simple list format (same as Reports page)
- Battery Pack ID shown as text
- No image previews in list
- Download button for each QR code
- File size and path information

**Features:**

**Search:**
- Type Battery Pack ID to filter results
- Real-time search as you type
- Shows count of matching results

**Sort Options:**
- Newest First
- Oldest First
- Name A-Z
- Name Z-A

**Individual Download:**
- Click "Download File" button next to any QR code
- Downloads as PNG file
- Filename: {Battery_Pack_ID}.png

**Bulk Download:**
- "Download All QR Codes as ZIP" button
- Creates timestamped ZIP file
- Contains all filtered QR codes
- Filename: QR_Codes_YYYYMMDD_HHMMSS.zip

---

## List Format

```
Search QR Codes: [___________]     Sort By: [Newest First]
Showing X of Y QR codes
---

PACK-001                                    [Download File]
Size: 12.3 KB | File: qr_codes/PACK-001.png
---

PACK-002                                    [Download File]
Size: 11.8 KB | File: qr_codes/PACK-002.png
---

PACK-003                                    [Download File]
Size: 12.1 KB | File: qr_codes/PACK-003.png
---

Bulk Actions
[Download All QR Codes as ZIP]
```

---

## Common Workflows

### Workflow 1: Re-download Lost QR Code

1. Go to QR Generator tab
2. Click "Saved QR Codes"
3. Search for battery pack ID
4. Click "Download File"
5. Print the QR code

### Workflow 2: Export All QR Codes

1. Go to "Saved QR Codes" tab
2. Click "Download All QR Codes as ZIP"
3. Save ZIP to backup location
4. Extract when needed

### Workflow 3: Download Specific Range

1. Go to "Saved QR Codes" tab
2. Search for common prefix (e.g., "PACK-1")
3. Click "Download All as ZIP"
4. Downloads only filtered results

---

## File Storage

**Location:** qr_codes/
**Format:** PNG images
**Naming:** {Battery_Pack_ID}.png
**Size:** Approximately 10-15 KB per file

**Example:**
```
qr_codes/
  ├── PACK-001.png
  ├── PACK-002.png
  ├── PACK-003.png
  └── ...
```

---

## Comparison with Reports Tab

Both tabs now use the same format:

| Feature | Reports | QR Codes |
|---------|---------|----------|
| List view | Yes | Yes |
| Search box | Yes | Yes |
| Sort options | Yes | Yes |
| Individual download | Yes | Yes |
| Bulk download | Yes | Yes (ZIP) |
| File info shown | Yes | Yes |
| Layout | Two columns | Two columns |

---

## Tips

**Batch Printing:**
1. Download all QR codes as ZIP
2. Extract to folder
3. Print all images in one job

**Search Shortcuts:**
- "PACK-1" shows PACK-1, PACK-10, PACK-100, etc.
- "2024" shows all with "2024" in name
- "TEST" shows all test battery packs

**Quality Settings:**
For printing, use 400px or 500px size with text label enabled.

---

## Troubleshooting

**"No QR codes found"**
Generate QR codes first in the "Generate New QR Code" tab.

**"Can't find specific QR code"**
Use the search box to filter by Battery Pack ID.

**"Need to re-generate QR code"**
The system prevents duplicates. Download the existing one instead.

---

## Access

URL: https://192.168.0.237:8501
Tab: QR Code Generator
Sub-tabs: Generate New QR Code | Saved QR Codes

---

Version: v2.6 - List Format QR Codes
Date: January 8, 2026
