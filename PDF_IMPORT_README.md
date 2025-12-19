# PDF Import System - Usage Guide

## Overview

The PDF import system extracts structured data from PA kennel inspection PDFs and imports it into the SQLite database with proper relationships.

## Quick Start

### Option 1: Import in Batches (Recommended)

Process PDFs in batches of 1000 for better control and progress tracking:

```bash
cd /Users/jjustinwilson/Desktop/kennel
source venv/bin/activate

# Process first 1000 PDFs
python import_pdfs.py --start 0 --end 1000

# Process next 1000 (skip schema update)
python import_pdfs.py --start 1000 --end 2000 --no-schema

# Process next batch
python import_pdfs.py --start 2000 --end 3000 --no-schema
```

### Option 2: Automated Batch Processing

Use the batch runner script to automatically process all PDFs in chunks:

```bash
cd /Users/jjustinwilson/Desktop/kennel

# Process all PDFs in batches of 1000
./run_batch_import.sh

# Resume from a specific point (e.g., after interruption at 5000)
./run_batch_import.sh 5000

# Process a specific range
./run_batch_import.sh 0 5000
```

### Option 3: Import All at Once

Process all PDFs in one go (will take several hours):

```bash
cd /Users/jjustinwilson/Desktop/kennel
source venv/bin/activate
python import_pdfs.py
```

## Command Line Options

```
python import_pdfs.py [OPTIONS]

Options:
  --start START      Start index (0-based) for batch processing
  --end END          End index (exclusive) for batch processing
  --no-schema        Skip schema update (use for subsequent batches)
  -h, --help         Show help message
```

## Progress Tracking

The import script shows:
- Real-time progress bar with percentage complete
- Current file being processed
- Elapsed time
- Checkpoint messages every 500 files
- Final statistics including:
  - PDFs processed
  - Successfully imported
  - Skipped (no database match)
  - Errors
  - Database statistics (violations, reinspections, etc.)

## Database Schema

### New Tables Created

1. **dog_counts** - Dog population data per inspection
   - Current year and previous year counts
   - Boarding, breeding, transfer, on-premises counts

2. **inspection_items** - Individual inspection category results
   - Kennel Regulations (21.x codes)
   - Kennel Acts (200/400 codes)
   - Miscellaneous items
   - Results: Satisfactory, Unsatisfactory, Not Applicable, Yes, No

### Extended Tables

**inspections** table gets new columns:
- inspector_name
- person_interviewed
- person_title
- inspection_action
- license_year_class
- remarks_text
- reinspection_required

## Performance

- Processing speed: ~50-100 PDFs per minute (varies by system)
- Total time for ~25,000 PDFs: 4-8 hours
- Batch processing recommended for:
  - Better progress tracking
  - Ability to pause/resume
  - Easier error recovery

## Resuming After Interruption

If the import is interrupted:

```bash
# Check how many were processed
sqlite3 kennel_inspections.db "SELECT COUNT(*) FROM inspections WHERE inspector_name IS NOT NULL"

# Resume from that point (e.g., if 3500 were done)
python import_pdfs.py --start 3500 --no-schema
```

## Example Queries After Import

```sql
-- Find all violations
SELECT k.name, i.inspection_date, ii.category_name, i.remarks_text
FROM kennels k
JOIN inspections i ON k.kennel_id = i.kennel_id
JOIN inspection_items ii ON i.id = ii.inspection_id
WHERE ii.result = 'Unsatisfactory'
ORDER BY i.inspection_date DESC;

-- Kennels requiring reinspection
SELECT k.name, k.county, i.inspection_date, i.inspector_name
FROM kennels k
JOIN inspections i ON k.kennel_id = i.kennel_id
WHERE i.reinspection_required = 1
ORDER BY i.inspection_date DESC;

-- Dog count trends for a specific kennel
SELECT i.inspection_date, 
       dc.boarding, dc.breeding, dc.on_prem
FROM inspections i
JOIN dog_counts dc ON i.id = dc.inspection_id
WHERE i.kennel_id = 12345 AND dc.year_type = 'current'
ORDER BY i.inspection_date;

-- Most common violations
SELECT ii.category_name, COUNT(*) as violation_count
FROM inspection_items ii
WHERE ii.result = 'Unsatisfactory'
GROUP BY ii.category_name
ORDER BY violation_count DESC
LIMIT 20;
```

## Troubleshooting

### "No PDF files found"
- Check that `kennel_inspections/` directory exists
- Verify PDFs are in county subdirectories

### "Failed to parse PDF"
- Some PDFs may have formatting issues
- These are skipped automatically
- Check error log for details

### Database locked
- Only one import process can run at a time
- Wait for current process to complete or kill it

### Memory issues
- Use batch processing with smaller batches
- Process 500-1000 PDFs at a time

## Files

- `pdf_parser.py` - PDF text extraction and parsing
- `db_importer.py` - Database schema and import functions
- `import_pdfs.py` - Main import script
- `run_batch_import.sh` - Automated batch processing
- `test_parser.py` - Parser testing utility
