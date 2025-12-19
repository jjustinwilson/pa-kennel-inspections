# Deploying to Render

This guide will walk you through deploying your PA Kennel Inspection web app to Render.

## What You Get with Render Free Tier

- **750 hours/month** of uptime (enough for ~31 days if always on)
- **512 MB RAM**
- **Automatic HTTPS**
- **Custom subdomain** (yourapp.onrender.com)
- Spins down after 15 minutes of inactivity
- Spins back up automatically when accessed (takes ~30 seconds)

## Important: Database Persistence

⚠️ **Render's free tier has ephemeral storage**, meaning:
- Your SQLite database (`kennel_inspections.db`) will be included in the deployment
- The database will be **read-only in practice** (any writes are lost on restart)
- Since your app is primarily for browsing data, this is perfect for your use case
- The database won't change unless you redeploy with an updated database file

For persistent database changes, you would need Render's paid tier with a persistent disk (~$7/month).

## Prerequisites

1. A GitHub account
2. Your project in a GitHub repository
3. The `kennel_inspections.db` file in your repo (make sure it's not gitignored)

## Deployment Steps

### Step 1: Prepare Your Repository

Make sure these files are in your repo:
- `app.py` - Your Flask application
- `requirements.txt` - Python dependencies (includes gunicorn)
- `render.yaml` - Render configuration (already created)
- `kennel_inspections.db` - Your SQLite database
- `templates/` - HTML templates folder
- `static/` - CSS/JS files folder

**Check your `.gitignore`**: Make sure `kennel_inspections.db` is NOT ignored!

```bash
# If db is ignored, remove it from .gitignore and commit
git add kennel_inspections.db
git commit -m "Add database for deployment"
git push
```

### Step 2: Connect to GitHub

1. Go to [render.com](https://render.com)
2. Sign up or log in (can use GitHub account)
3. Click **"New +"** → **"Web Service"**
4. Click **"Connect GitHub"** and authorize Render
5. Select your repository from the list

### Step 3: Configure the Service

Render should auto-detect your `render.yaml` configuration. If not, configure manually:

- **Name**: `pa-kennel-inspections` (or your choice)
- **Region**: Choose closest to you
- **Branch**: `main` (or your default branch)
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`
- **Plan**: `Free`

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will start building your app
3. Wait 2-5 minutes for the build to complete
4. You'll see the live URL: `https://pa-kennel-inspections.onrender.com`

### Step 5: Test Your App

Visit your live URL and test:
- ✅ Home page loads with statistics
- ✅ Search for kennels works
- ✅ Kennel detail pages display
- ✅ Inspection detail pages show full data
- ✅ Violations page displays

## Monitoring

On your Render dashboard you can:
- View logs (useful for debugging)
- Monitor service status
- See request metrics
- Manually restart service if needed

## Important Notes

### Database Size
Your `kennel_inspections.db` is likely **large** (hundreds of MBs). GitHub has:
- File size limit: 100 MB recommended, 100 MB warning
- Repository size limit: 1 GB soft limit

If your database is too large for GitHub:

**Option A: Use Git LFS (Large File Storage)**
```bash
# Install git-lfs
brew install git-lfs  # macOS
# or apt-get install git-lfs  # Linux

# Initialize in your repo
git lfs install
git lfs track "*.db"
git add .gitattributes
git add kennel_inspections.db
git commit -m "Track database with LFS"
git push
```

**Option B: Use a smaller database**
```bash
# Create a subset of your data for demo purposes
sqlite3 kennel_inspections.db "CREATE DATABASE kennel_demo.db AS SELECT * FROM kennels LIMIT 100;"
# Then deploy with kennel_demo.db instead
```

### Performance

The free tier has limited resources:
- 512 MB RAM (your database needs to fit in memory)
- Shared CPU
- Spins down after 15 minutes idle
- First request after spin-down takes ~30 seconds

For better performance, upgrade to paid tier ($7/month).

### Auto-Deploy

Render automatically deploys when you push to your main branch:
```bash
# Make changes
git add .
git commit -m "Update database with new inspections"
git push

# Render auto-deploys in 2-5 minutes
```

## Updating Your Database

To update the database with new inspection data:

1. Run your import locally:
```bash
python import_pdfs.py --workers 8 --skip-existing
```

2. Commit and push the updated database:
```bash
git add kennel_inspections.db
git commit -m "Update inspections data"
git push
```

3. Render automatically redeploys with new data

## Troubleshooting

### Build fails
- Check logs on Render dashboard
- Verify `requirements.txt` has all dependencies
- Ensure Python version compatibility

### App won't start
- Check that `app.py` is in root directory
- Verify `gunicorn app:app` command is correct
- Check logs for Python errors

### Database not found
- Ensure `kennel_inspections.db` is committed to repo
- Check that it's not in `.gitignore`
- Verify file path in `app.py` (should be just `"kennel_inspections.db"`)

### App is slow
- First request after idle will be slow (cold start)
- Consider upgrading to paid tier to avoid spin-down
- Database queries might need optimization for large datasets

## Alternative: Render Persistent Disk (Paid)

If you need writable database persistence:

1. Upgrade to Starter plan ($7/month)
2. Add a persistent disk to your service
3. Mount at `/mnt/data`
4. Update `app.py` to use `/mnt/data/kennel_inspections.db`

This allows database writes to persist between deploys and restarts.

## Cost Estimate

- **Free tier**: $0/month (750 hours, good for brief/demo use)
- **Starter tier**: $7/month (persistent disk, always-on)
- **Pro tier**: $25/month (more resources, better performance)

## Summary

✅ **Best for**: Demos, temporary access, read-only apps
✅ **Free tier works great** for your use case (browsing inspection data)
✅ **Easy deployment**: Push to GitHub → auto-deploys
⚠️ **Database is read-only** on free tier (perfect for your needs)
⚠️ **Spins down** after 15 minutes (30s wake-up time)

Your app should be live at: `https://pa-kennel-inspections.onrender.com`

Enjoy! 🚀
