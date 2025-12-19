# ⚡ Quick Reference - PDF Import

## 🚀 Start Importing (Recommended)

```bash
cd /Users/jjustinwilson/Desktop/kennel
./run_batch_import.sh
```

**What this does:**
- Processes all 46,706 PDFs
- Uses 8 parallel workers
- Batches of 1,000 PDFs
- **Skips already imported** (smart resume!)
- **Completes in ~2-3 hours**

---

## 📊 Check Progress

```bash
python check_progress.py
```

---

## 🔄 Resume After Interruption

```bash
# Check where you stopped
python check_progress.py

# Resume from any point (skips already done)
./run_batch_import.sh 0
# OR resume from specific point
./run_batch_import.sh 5000
```

**Note:** Skip-existing is enabled by default - it automatically skips imported PDFs!

---

## ⚙️ Custom Settings

### Use Fewer Workers (Less CPU)
```bash
./run_batch_import.sh 0 0 4
```

### Smaller Batches
```bash
./run_batch_import.sh 0 0 8 500
```

### Maximum Speed
```bash
./run_batch_import.sh 0 0 12 2000
```

---

## 📝 Parameters

```bash
./run_batch_import.sh [START] [END] [WORKERS] [BATCH_SIZE]
```

| Parameter | Default | Example |
|-----------|---------|---------|
| START | 0 | 5000 |
| END | all | 10000 |
| WORKERS | 8 | 4 or 12 |
| BATCH_SIZE | 1000 | 500 or 2000 |

---

## ⏱️ Expected Time

| Workers | Total Time |
|---------|------------|
| 4 | ~4 hours |
| 8 | ~2-3 hours |
| 12 | ~1.5-2 hours |

---

## ✅ Current Status

**Your Progress:** ~1,000 / 46,706 PDFs (2%)

**To Complete:**
```bash
./run_batch_import.sh 1000
```

**Time Remaining:** ~2-3 hours with 8 workers

---

## 🌐 View Results

```bash
./start_web.sh
```

Then open: http://localhost:5000

---

That's it! Just run `./run_batch_import.sh` and you're done! 🎉
