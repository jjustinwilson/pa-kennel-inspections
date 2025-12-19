# 🐕 PA Kennel Inspection Database

Complete system for scraping, importing, and browsing Pennsylvania kennel inspection reports.

## 📦 What's Included

### 1. Web Scraper
- Downloads inspection PDFs from PA Department of Agriculture
- Organizes by county and kennel
- Stores metadata in SQLite database
- **Parallel processing** with 5 workers

### 2. PDF Parser & Importer
- Extracts structured data from PDFs
- **Parallel processing** with up to 12 workers
- Imports inspection details, dog counts, violations
- Batch processing with resume capability

### 3. Web Application
- Browse kennels and inspections
- Search and filter functionality
- View detailed inspection reports
- Track violations and trends

---

## 🚀 Quick Start

### 1. Scrape PDFs (If Needed)
```bash
cd /Users/jjustinwilson/Desktop/kennel
source venv/bin/activate
python scraper.py
```

### 2. Import PDF Data
```bash
./run_batch_import.sh
```
**Time:** ~2-3 hours with 8 workers

### 3. Browse Data
```bash
./start_web.sh
```
**Access:** http://localhost:5000

---

## 📊 Current Status

- **PDFs Downloaded:** 46,706
- **PDFs Imported:** ~1,000 (2%)
- **Kennels:** ~90
- **Inspections:** ~7,000
- **Violations:** ~1,000

---

## 📚 Documentation

### Getting Started
- `QUICK_START.md` - Quick start guide
- `IMPORT_QUICK_REF.md` - Import quick reference

### PDF Import
- `PDF_IMPORT_README.md` - Complete import guide
- `BATCH_IMPORT_USAGE.md` - Batch script usage
- `PARALLEL_PROCESSING_GUIDE.md` - Parallel processing details
- `SPEEDUP_COMPLETE.md` - Performance improvements

### Web Application
- `WEB_APP_README.md` - Web app usage guide
- `QUICK_START_WEB.md` - Web app quick start
- `WEB_APP_COMPLETE.md` - Implementation details

### Other
- `BEFORE_VS_AFTER.md` - Scraper improvements
- `IMPROVEMENTS.md` - Scraper parallelization

---

## 🛠️ Components

### Scraper (`scraper.py`)
- Downloads PDFs from PA website
- 5 parallel workers
- Organizes by county/kennel
- Stores metadata in database

### PDF Parser (`pdf_parser.py`)
- Extracts text from PDFs
- Parses structured data
- Handles multiple PDF formats

### Database Importer (`db_importer.py`)
- Updates database schema
- Imports parsed data
- Maintains relationships

### Import Script (`import_pdfs.py`)
- Main import orchestrator
- Parallel processing (1-12 workers)
- Batch processing
- Progress tracking

### Batch Runner (`run_batch_import.sh`)
- Automated batch processing
- Default: 8 workers, 1000 per batch
- Error handling and resume

### Web App (`app.py`)
- Flask web application
- Search and browse interface
- Detailed inspection reports
- Violation tracking

### Progress Checker (`check_progress.py`)
- Shows import statistics
- Violation analysis
- Resume instructions

---

## ⚡ Performance

### Scraper
- **Speed:** ~60 PDFs/minute
- **Time:** ~13 hours for all counties
- **Workers:** 5 parallel

### PDF Import
| Workers | Speed | Total Time |
|---------|-------|------------|
| 1 | 60/min | ~13 hours |
| 4 | 180/min | ~4 hours |
| 8 | 300/min | ~2-3 hours |
| 12 | 400/min | ~1.5-2 hours |

---

## 💾 Database Schema

### Tables
- **kennels** - Kennel information
- **inspections** - Inspection metadata
- **dog_counts** - Dog population data
- **inspection_items** - Inspection findings

### Relationships
- Many inspections → One kennel
- Many inspection_items → One inspection
- Many dog_counts → One inspection

---

## 🎯 Common Tasks

### Complete the Import
```bash
./run_batch_import.sh 1000
```

### Check Progress
```bash
python check_progress.py
```

### Start Web App
```bash
./start_web.sh
```

### Resume After Error
```bash
# Check where you stopped
python check_progress.py

# Resume from that point
./run_batch_import.sh <NUMBER>
```

---

## 📝 Example Queries

```sql
-- Find all violations
SELECT k.name, i.inspection_date, ii.category_name
FROM kennels k
JOIN inspections i ON k.kennel_id = i.kennel_id
JOIN inspection_items ii ON i.id = ii.inspection_id
WHERE ii.result = 'Unsatisfactory';

-- Kennels requiring reinspection
SELECT k.name, k.county, i.inspection_date
FROM kennels k
JOIN inspections i ON k.kennel_id = i.kennel_id
WHERE i.reinspection_required = 1;

-- Dog count trends
SELECT i.inspection_date, dc.breeding, dc.on_prem
FROM inspections i
JOIN dog_counts dc ON i.id = dc.inspection_id
WHERE i.kennel_id = ? AND dc.year_type = 'current';
```

---

## 🔧 Requirements

- Python 3.8+
- SQLite3
- pdftotext (via Homebrew)
- Virtual environment with packages:
  - requests
  - beautifulsoup4
  - rich
  - flask

---

## 📁 File Structure

```
kennel/
├── scraper.py              # PDF scraper
├── pdf_parser.py           # PDF text parser
├── db_importer.py          # Database importer
├── import_pdfs.py          # Main import script
├── app.py                  # Web application
├── check_progress.py       # Progress checker
├── run_batch_import.sh     # Batch runner
├── start_web.sh            # Web app starter
├── kennel_inspections.db   # SQLite database
├── kennel_inspections/     # Downloaded PDFs
├── templates/              # Web app templates
├── static/                 # Web app assets
└── venv/                   # Python virtual env
```

---

## 🎉 Summary

This is a complete system for:
- ✅ Scraping kennel inspection PDFs
- ✅ Parsing and importing structured data
- ✅ Browsing through web interface
- ✅ Analyzing violations and trends

**Next Step:** Run `./run_batch_import.sh` to complete the import! 🚀
