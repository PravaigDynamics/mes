# Battery Pack MES (Manufacturing Execution System)

**Version**: 2.2 (Database Edition)
**Status**: Production Ready
**Deployment**: VM Server (Local Network)

---

## Overview

Professional Manufacturing Execution System for Battery Pack Production with database-backed storage, real-time QC tracking, automatic backups, and comprehensive production analytics.

---

## Key Features

- **Database Storage**: SQLite with PostgreSQL support for data persistence
- **Automatic Backups**: Backup after every data entry and process completion
- **Real-Time Dashboard**: Live production tracking and analytics
- **QR Code Scanning**: Photo upload and live camera scanning
- **Excel Integration**: Generate reports in exact template format from database
- **8-Stage Process Tracking**: Complete workflow management
- **Professional UI**: Clean, emoji-free enterprise interface
- **Concurrent Access**: Multi-user support via database backend

---

## System Requirements

**Minimum**:
- Python 3.8+
- 2 CPU cores
- 4GB RAM
- 20GB disk space

**Recommended**:
- Python 3.9+
- 4 CPU cores
- 8GB RAM
- 50GB disk space

---

## Quick Start

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

pip install -r requirements_new.txt
```

### 2. Run Application
```bash
streamlit run app_unified_db.py --server.port 8501 --server.address 0.0.0.0
```

### 3. Access
- **Local**: http://localhost:8501
- **Network**: http://[SERVER_IP]:8501

---

## Production Deployment

For VM server deployment, see **[VM_DEPLOYMENT_GUIDE.md](VM_DEPLOYMENT_GUIDE.md)**

The deployment guide includes:
- VM setup instructions
- Systemd/Windows service configuration
- Firewall configuration
- Automatic startup
- Backup strategies
- Troubleshooting

---

## Application Structure

```
d:\MES\
├── app_unified_db.py       # Main application
├── database.py             # Database layer (SQLite/PostgreSQL)
├── excel_generator.py      # Excel file generator
├── backup_manager.py       # Automatic backup system
├── sample.xlsx             # Excel template (REQUIRED)
├── battery_mes.db          # Production database
├── requirements_new.txt    # Python dependencies
├── backups/                # Automatic backup storage
├── excel_reports/          # Generated Excel files
└── qr_codes/              # Generated QR codes
```

---

## Core Technologies

- **Backend**: Python 3.8+
- **Database**: SQLite (upgradable to PostgreSQL)
- **Web Framework**: Streamlit
- **Excel**: openpyxl
- **QR Processing**: OpenCV, qrcode
- **Data Processing**: pandas, numpy
- **Charts**: plotly

---

## Production Workflow

1. **Scan QR Code** (or manual entry)
2. **Select Process** (Cell sorting → Ready for Dispatch)
3. **Enter QC Data** (Module X/Y results, technician info)
4. **Save** (automatic backup created)
5. **Complete Process** (when ready, marks end date)
6. **View Dashboard** (real-time tracking)
7. **Download Reports** (Excel, CSV)

---

## Process Stages

1. Cell sorting
2. Module assembly
3. Pre Encapsulation
4. Wire Bonding
5. Post Encapsulation
6. EOL Testing
7. Pack assembly
8. Ready for Dispatch

---

## Data Reliability

- **Database as source of truth**: All data stored in SQLite database
- **Excel as export format**: Generated from database on-demand
- **Automatic backups**: Created after every save/complete action
- **Retention**: Last 30 backups maintained automatically
- **Manual backup**: Available anytime via Reports tab

---

## Features Overview

### Data Entry
- QR code scanning (camera + photo upload)
- Manual battery pack ID entry
- Process selection with workflow
- QC check recording (Module X/Y)
- Input validation
- Automatic backup after save

### Dashboard
- Real-time battery pack tracker
- 8-stage process visualization
- Production charts (Plan vs Actual)
- Color-coded status indicators
- Refresh on demand

### Reports
- Individual battery pack downloads
- Master Excel file with all packs
- CSV export for analysis
- Search and filter
- Backup management section

### QR Generator
- Batch QR code generation
- Customizable size
- Label support
- PNG download
- Duplicate detection

---

## Security & Access

**For Local VM Deployment:**
- No authentication required (trusted local network)
- Firewall restricts to local network only
- Data stays on premises
- No internet access required
- Backup system for data protection

**Recommended after 1 month:**
- Get user feedback
- Add authentication if needed
- Enhance based on actual usage

---

## Backup Strategy

**Automatic Backups**:
- After every data entry save
- After every process completion
- Timestamped filename format
- Stored in `backups/` folder
- Keeps last 30 backups

**Manual Backups**:
- "Create Backup Now" button in Reports tab
- Backup history viewer
- Database size display

**Recommended Additional Backups**:
- Weekly: Copy to external USB drive
- Monthly: Upload to cloud storage
- Before updates: Always create manual backup

---

## Browser Support

- Chrome (Recommended)
- Edge
- Firefox
- Safari

---

## Performance

- **Concurrent Users**: 10+ users simultaneously
- **Database**: Handles 1000+ battery packs
- **Backup Speed**: < 1 second
- **Excel Generation**: < 2 seconds
- **Dashboard Load**: < 1 second

---

## Maintenance

### Database
- Automatic backup after each change
- Manual backup button available
- Backup verification built-in
- Easy restore functionality

### Updates
1. Create manual backup
2. Pull new code
3. Restart service
4. Verify functionality

### Monitoring
- Check backup folder regularly
- Monitor disk space
- Review application logs
- Test concurrent access periodically

---

## Troubleshooting

**Issue**: Cannot access from other PCs
**Fix**: Check firewall allows port 8501

**Issue**: Database locked
**Fix**: Restart application service

**Issue**: Excel not downloading
**Fix**: Check `excel_reports/` folder exists, restart app

See [VM_DEPLOYMENT_GUIDE.md](VM_DEPLOYMENT_GUIDE.md) for detailed troubleshooting.

---

## Support

**Deployment**: See VM_DEPLOYMENT_GUIDE.md
**Architecture**: Database-backed with Excel export
**Version**: 2.2 (Professional Edition)

---

## Version History

**v2.2 (2025-12-31)** - Database Edition
- Migrated to database backend (SQLite/PostgreSQL)
- Automatic backup after every data change
- Professional UI (no emojis)
- Improved button visibility
- Enhanced data reliability
- Concurrent user support

---

**License**: Proprietary - Internal Use Only
**Prepared**: 2025-12-31
**Status**: Production Ready for VM Deployment
