# 🚀 Batch Import Script - Usage Guide

## Quick Start

### Process All PDFs (Recommended)
```bash
./run_batch_import.sh
```

This will:
- Process all 46,706 PDFs
- Use 8 parallel workers
- Process in batches of 1,000
- Complete in ~2-3 hours

---

## Usage

```bash
./run_batch_import.sh [START] [END] [WORKERS] [BATCH_SIZE]
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| START | 0 | Starting PDF index (0-based) |
| END | all | Ending PDF index (0 = process all) |
| WORKERS | 8 | Number of parallel workers |
| BATCH_SIZE | 1000 | PDFs per batch |

---

## Examples

### 1. Process Everything (Default)
```bash
./run_batch_import.sh
```
- Starts at 0
- Processes all PDFs
- Uses 8 workers
- Batches of 1,000

### 2. Resume from Specific Point
```bash
./run_batch_import.sh 5000
```
- Starts at PDF 5000
- Processes to end
- Uses 8 workers
- Batches of 1,000

### 3. Process Specific Range
```bash
./run_batch_import.sh 0 10000
```
- Processes PDFs 0-10,000
- Uses 8 workers
- Batches of 1,000

### 4. Use Different Worker Count
```bash
./run_batch_import.sh 0 0 4
```
- Processes all PDFs
- Uses 4 workers (slower but less CPU)
- Batches of 1,000

### 5. Custom Batch Size
```bash
./run_batch_import.sh 0 0 8 500
```
- Processes all PDFs
- Uses 8 workers
- Batches of 500 (smaller batches)

### 6. Maximum Speed
```bash
./run_batch_import.sh 0 0 12 2000
```
- Processes all PDFs
- Uses 12 workers (if you have cores)
- Batches of 2,000 (larger batches)

---

## What It Does

### Automatic Features
1. ✅ Counts total PDFs
2. ✅ Processes in batches
3. ✅ Updates schema on first batch only
4. ✅ Shows progress for each batch
5. ✅ Handles errors gracefully
6. ✅ Provides resume instructions

### Batch Processing
```
Batch 1:    0 - 1,000   (schema update)
Batch 2:  1,000 - 2,000  (no schema)
Batch 3:  2,000 - 3,000  (no schema)
...
Batch 47: 46,000 - 46,706 (no schema)
```

### Parallel Workers
Each batch uses 8 workers processing PDFs simultaneously:
```
Worker 1: PDF 0, 8, 16, 24...
Worker 2: PDF 1, 9, 17, 25...
Worker 3: PDF 2, 10, 18, 26...
...
Worker 8: PDF 7, 15, 23, 31...
```

---

## Performance

### With Default Settings (8 workers, 1000 batch)
- **Speed**: ~240-300 PDFs/minute
- **Time per batch**: ~3-4 minutes
- **Total time**: ~2-3 hours for all 46,706 PDFs

### Comparison
| Workers | Batch Size | Time per 1000 | Total Time |
|---------|------------|---------------|------------|
| 1 | 1000 | 15-20 min | ~13 hours |
| 4 | 1000 | 5-7 min | ~4 hours |
| 8 | 1000 | 3-4 min | ~2-3 hours |
| 12 | 1000 | 2-3 min | ~1.5-2 hours |

---

## Error Handling

If an error occurs:
```
Error in batch 5000-6000
Resume with: ./run_batch_import.sh 5000
```

Just run the suggested command to resume!

---

## Monitoring Progress

### Check Progress Anytime
```bash
# In another terminal
python check_progress.py
```

### Watch Progress Live
```bash
# Update every 30 seconds
watch -n 30 'python check_progress.py'
```

---

## Tips

### For Fastest Import
```bash
# Use 12 workers, larger batches
./run_batch_import.sh 0 0 12 2000
```

### For System Stability
```bash
# Use 4 workers, smaller batches
./run_batch_import.sh 0 0 4 500
```

### For Testing
```bash
# Process just 100 PDFs
./run_batch_import.sh 0 100 8 100
```

### Resume After Interruption
```bash
# Check where you stopped
python check_progress.py

# Resume from that point (e.g., 15000)
./run_batch_import.sh 15000
```

---

## Current Status

Your import is at ~1,000 PDFs out of 46,706.

### To Complete Quickly
```bash
# Resume with 8 workers (2-3 hours remaining)
./run_batch_import.sh 1000
```

### To Continue Safely
```bash
# Resume with 4 workers (4 hours remaining)
./run_batch_import.sh 1000 0 4
```

---

## Summary

**Default command:**
```bash
./run_batch_import.sh
```

**This gives you:**
- ✅ 8 parallel workers (4-5x faster)
- ✅ Batches of 1,000 PDFs
- ✅ Automatic error handling
- ✅ Progress tracking
- ✅ Resume capability
- ✅ ~2-3 hours for full import

**Just run it and let it complete!** 🚀
