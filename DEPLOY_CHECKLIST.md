# Render Deployment Checklist

Quick checklist to deploy your PA Kennel Inspection app to Render.

## Pre-Deployment Checklist

- [ ] **Database is ready**: `kennel_inspections.db` exists and has data
- [ ] **Requirements are up to date**: `requirements.txt` includes all dependencies
- [ ] **Database not ignored**: Check `.gitignore` doesn't exclude `*.db`
- [ ] **Check database size**: Run `ls -lh kennel_inspections.db`
  - If > 100 MB, consider using Git LFS or a subset for demo

## Quick Commands

### 1. Check Database Size
```bash
ls -lh kennel_inspections.db
du -h kennel_inspections.db
```

### 2. Check Git Status
```bash
# Make sure database is tracked
git ls-files | grep kennel_inspections.db

# If not tracked, add it
git add kennel_inspections.db
```

### 3. Commit and Push (if needed)
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

## Deployment Steps

1. **Go to Render**: https://render.com
2. **Sign in** with GitHub
3. **New Web Service** → Connect your repository
4. **Accept defaults** (render.yaml will configure everything)
5. **Deploy** and wait 2-5 minutes
6. **Visit your URL**: `https://your-app-name.onrender.com`

## Post-Deployment

- [ ] **Test home page**: Loads and shows statistics
- [ ] **Test search**: Find a kennel and view details
- [ ] **Test inspection**: View a full inspection report
- [ ] **Check violations**: View the violations page
- [ ] **Bookmark your URL**: Save it for future access

## If Database is Too Large for GitHub

### Option A: Use Git LFS
```bash
# Install git-lfs
brew install git-lfs

# Track database files
git lfs install
git lfs track "*.db"
git add .gitattributes
git add kennel_inspections.db
git commit -m "Track database with LFS"
git push
```

### Option B: Create a Smaller Demo Database
```bash
# Create a subset with first 1000 kennels
sqlite3 kennel_inspections.db <<EOF
ATTACH DATABASE 'kennel_demo.db' AS demo;
CREATE TABLE demo.kennels AS SELECT * FROM kennels LIMIT 1000;
CREATE TABLE demo.inspections AS SELECT * FROM inspections WHERE kennel_id IN (SELECT id FROM demo.kennels);
CREATE TABLE demo.inspection_items AS SELECT * FROM inspection_items WHERE inspection_id IN (SELECT id FROM demo.inspections);
CREATE TABLE demo.dog_counts AS SELECT * FROM dog_counts WHERE inspection_id IN (SELECT id FROM demo.inspections);
EOF

# Use the demo database
mv kennel_inspections.db kennel_inspections_full.db
mv kennel_demo.db kennel_inspections.db
```

## Troubleshooting

### Build Fails
1. Check Render logs for error messages
2. Test locally: `gunicorn app:app`
3. Verify all files are committed

### Database Not Found
1. Confirm file is in repo: `git ls-files | grep .db`
2. Check it's not gitignored: `git check-ignore kennel_inspections.db`
3. Verify path in app.py is just `"kennel_inspections.db"`

### App is Slow
- **First load**: Takes 30s if app was sleeping (free tier)
- **Large database**: Consider optimizing queries or using indexes
- **Upgrade**: Paid tier ($7/month) for always-on service

## Your URLs

After deployment, save these:
- **App URL**: `https://pa-kennel-inspections.onrender.com`
- **Dashboard**: `https://dashboard.render.com/`
- **Logs**: Available in Render dashboard

## Quick Stats

Current database contains:
```bash
# Run this to see your stats
sqlite3 kennel_inspections.db "
SELECT 
    'Kennels: ' || COUNT(*) FROM kennels
UNION ALL
SELECT 'Inspections: ' || COUNT(*) FROM inspections
UNION ALL
SELECT 'Violations: ' || COUNT(*) FROM inspection_items WHERE result='Unsatisfactory';
"
```

## Done! 🎉

Your app should be live at Render. Share the URL and enjoy your deployed kennel inspection browser!
