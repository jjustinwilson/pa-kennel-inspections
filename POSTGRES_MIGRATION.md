# PostgreSQL Migration Guide

This guide explains the PostgreSQL migration for deploying the PA Kennel Inspections app on Render.

## Why PostgreSQL?

The full SQLite database (171MB) was too large for Render's free tier (512MB RAM). The Flask app would load the entire database into memory, causing worker timeouts and OOM kills.

**PostgreSQL Solution:**
- Database runs in a separate container
- Flask app only loads query results (not the entire database)
- Much lower memory footprint (~200MB vs 512MB+)
- Can handle the full dataset (4,345 kennels, 45,000+ inspections)

## What Changed

### 1. Database Connection (`app.py`)
- **Before:** `sqlite3.connect()` with local file
- **After:** `psycopg2.connect()` with DATABASE_URL from environment

### 2. SQL Query Syntax
- **Before:** SQLite placeholders `?`
- **After:** PostgreSQL placeholders `%s`

### 3. Dependencies (`requirements.txt`)
- Added: `psycopg2-binary>=2.9.9`

### 4. Render Configuration (`render.yaml`)
- Added PostgreSQL database service: `pakenneldb`
- Web service gets DATABASE_URL automatically via `fromDatabase`

### 5. Data Migration
- Created `migrate_to_postgres.py` script
- Migrates all tables from SQLite to PostgreSQL
- Handles ID mapping for foreign keys
- Uses batch inserts for performance

## Deployment Steps

### Step 1: Deploy to Render

The `render.yaml` file will automatically create both services:
1. PostgreSQL database (`pakenneldb`)
2. Web service (Flask app)

1. Go to https://dashboard.render.com/
2. Click **"New +" → "Blueprint"**
3. Select repository: `pa-kennel-inspections`
4. Branch: `postgres-migration`
5. Click **"Apply"**

Render will:
- Create the PostgreSQL database
- Build and deploy the web service
- Connect them via DATABASE_URL environment variable

### Step 2: Migrate Data

Once deployed, you need to populate the PostgreSQL database with your data.

#### Option A: Run Migration from Local Machine

```bash
# Get the DATABASE_URL from Render dashboard
# It will look like: postgres://user:pass@host/pakenneldb

# Set environment variable
export DATABASE_URL="your-database-url-from-render"

# Make sure you have the full database locally
ls -lh kennel_inspections_FULL.db  # Should be ~171MB

# Run migration script
python migrate_to_postgres.py
```

**Expected output:**
```
============================================================
SQLite to PostgreSQL Migration
============================================================

Source: kennel_inspections_FULL.db
Target: postgresql://...

Connecting to databases...
✓ Connected

Creating PostgreSQL schema...
✓ Schema created

Migrating kennels...
  Total kennels to migrate: 4345
  Migrated 4345 kennels

Migrating inspections...
  Total inspections to migrate: 45739
  Migrated 45739 inspections

Migrating dog counts...
  Migrated 54672 dog count records

Migrating inspection items...
  Migrated 987389 inspection items

============================================================
✓ Migration completed successfully!
============================================================
```

**Time estimate:** 5-10 minutes depending on connection speed.

#### Option B: Run Migration on Render (One-off Job)

If you can't run locally, you can run the migration as a one-off job on Render:

1. Upload `kennel_inspections_FULL.db` to a cloud storage (e.g., Dropbox, Google Drive)
2. Modify migration script to download from cloud storage
3. Run as Render one-off job via dashboard or CLI

### Step 3: Verify Deployment

Once migration completes, visit your app:
- URL: `https://pa-kennel-inspections.onrender.com`
- Test home page loads with correct statistics
- Search for kennels
- View kennel details and inspections
- Check violations page

## Database Schema

PostgreSQL schema matches SQLite exactly:

```sql
-- Kennels table
kennels (
    kennel_id INTEGER PRIMARY KEY,
    name TEXT,
    license_number TEXT,
    county TEXT,
    city TEXT,
    last_status TEXT,
    last_inspection_date TEXT,
    pdf_path TEXT
)

-- Inspections table
inspections (
    id SERIAL PRIMARY KEY,
    kennel_id INTEGER,
    inspection_date TEXT,
    pdf_path TEXT,
    inspector_name TEXT,
    inspection_type TEXT,
    inspection_action TEXT,
    reinspection_required BOOLEAN,
    followup_date TEXT,
    license_expires TEXT,
    remarks TEXT
)

-- Dog counts table
dog_counts (
    id SERIAL PRIMARY KEY,
    inspection_id INTEGER,
    year_type TEXT,
    breeding INTEGER,
    boarding INTEGER,
    on_prem INTEGER,
    transfer INTEGER
)

-- Inspection items table
inspection_items (
    id SERIAL PRIMARY KEY,
    inspection_id INTEGER,
    category_name TEXT,
    category_code TEXT,
    category_section TEXT,
    result TEXT
)
```

## Performance Optimizations

The migration script includes:
- Batch inserts (1000 records at a time)
- Database indices on common query fields
- Proper foreign key constraints
- Commit batching for speed

PostgreSQL configuration in app:
- Connection pooling ready (gunicorn handles this)
- Cursor management (proper open/close)
- Dictionary cursor for easy Row access

## Costs

### Free Tier
- **PostgreSQL:** 256MB storage (plenty for 171MB database)
- **Web Service:** 512MB RAM, 750 hours/month
- **Total:** $0/month

**Limitations:**
- Database expires after 90 days (re-create or upgrade)
- Web service spins down after 15 min idle

### Paid Tier (Optional)
- **Starter PostgreSQL:** $7/month (persistent, no expiration)
- **Starter Web Service:** $7/month (always-on, more RAM)
- **Total:** $14/month for production use

## Troubleshooting

### Migration Fails: "relation already exists"
The script handles this with `IF NOT EXISTS` clauses. If you need to start fresh:

```sql
-- Connect to PostgreSQL and drop all tables
DROP TABLE IF EXISTS inspection_items CASCADE;
DROP TABLE IF EXISTS dog_counts CASCADE;
DROP TABLE IF EXISTS inspections CASCADE;
DROP TABLE IF EXISTS kennels CASCADE;
```

Then re-run the migration script.

### App Can't Connect to Database
Check that DATABASE_URL is set correctly:
1. In Render dashboard, go to your web service
2. Check "Environment" tab
3. Verify DATABASE_URL is present and points to pakenneldb

### Queries are Slow
Add more indices if needed:

```sql
CREATE INDEX idx_kennels_license ON kennels(license_number);
CREATE INDEX idx_inspections_action ON inspections(inspection_action);
```

## Rollback to SQLite

If you need to rollback to SQLite (main branch):

```bash
git checkout main
git push origin main --force
```

Then redeploy from main branch on Render.

## Next Steps

After successful deployment:
- ✅ Full dataset available online
- ✅ Better performance than SQLite
- ✅ Lower memory usage
- ✅ Professional database setup
- ✅ Ready for production use

Consider:
- Setting up automated backups of PostgreSQL database
- Monitoring query performance
- Adding caching layer (Redis) if needed
- Upgrading to paid tier for 24/7 availability

## Support

For issues:
1. Check Render logs for errors
2. Verify DATABASE_URL connection string
3. Test migration script locally first
4. Review PostgreSQL logs in Render dashboard

---

**Branch:** `postgres-migration`  
**Status:** Ready for deployment  
**Last Updated:** December 19, 2024
