#!/bin/bash
# Batch PDF Import Runner
# Processes PDFs in batches of 1000 with 8 parallel workers
# Usage: ./run_batch_import.sh [START] [END] [WORKERS] [BATCH_SIZE] [--no-skip]

BATCH_SIZE=${4:-1000}  # Default: 1000 PDFs per batch
START=${1:-0}          # Default: start at 0
END=${2:-0}            # Default: process all
WORKERS=${3:-8}        # Default: 8 parallel workers
SKIP_EXISTING="--skip-existing"  # Default: skip already imported

# Check for --no-skip flag
if [[ "$5" == "--no-skip" ]] || [[ "$1" == "--no-skip" ]] || [[ "$2" == "--no-skip" ]] || [[ "$3" == "--no-skip" ]] || [[ "$4" == "--no-skip" ]]; then
    SKIP_EXISTING=""
fi

cd /Users/jjustinwilson/Desktop/kennel
source venv/bin/activate

# Get total PDF count
TOTAL=$(find kennel_inspections -name "*.pdf" -type f | wc -l | tr -d ' ')
echo "=========================================="
echo "PA Kennel Inspection Batch Import"
echo "=========================================="
echo "Total PDFs found: $TOTAL"
echo "Batch size: $BATCH_SIZE PDFs per batch"
echo "Parallel workers: $WORKERS"
if [ -n "$SKIP_EXISTING" ]; then
    echo "Skip mode: ENABLED (faster resume)"
else
    echo "Skip mode: DISABLED (re-import all)"
fi

# If no end specified, process all
if [ "$END" -eq 0 ]; then
    END=$TOTAL
fi

echo "Processing range: $START to $END"
echo "=========================================="
echo ""

# Process in batches
CURRENT=$START
SCHEMA_FLAG=""

while [ $CURRENT -lt $END ]; do
    BATCH_END=$((CURRENT + BATCH_SIZE))
    if [ $BATCH_END -gt $END ]; then
        BATCH_END=$END
    fi
    
    echo "=========================================="
    echo "Batch: $CURRENT to $BATCH_END"
    echo "=========================================="
    
    # Skip schema update after first batch
    if [ $CURRENT -gt $START ]; then
        SCHEMA_FLAG="--no-schema"
    fi
    
    python import_pdfs.py --start $CURRENT --end $BATCH_END $SCHEMA_FLAG --workers $WORKERS $SKIP_EXISTING
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "Error in batch $CURRENT-$BATCH_END"
        echo "Resume with: ./run_batch_import.sh $CURRENT"
        exit 1
    fi
    
    CURRENT=$BATCH_END
    echo ""
done

echo ""
echo "=========================================="
echo "✓ All batches complete!"
echo "=========================================="
echo ""
echo "To check results, run: python check_progress.py"
