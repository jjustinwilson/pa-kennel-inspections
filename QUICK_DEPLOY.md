# Quick Deploy to Render

## ⚠️ Important: Database is 136MB

Your `kennel_inspections.db` is **136MB**, which exceeds GitHub's 100MB file limit.

**You have 2 options:**

### Option 1: Use Git LFS (Recommended)
```bash
# Install Git LFS
brew install git-lfs

# Set up LFS for your repo
git lfs install
git lfs track "*.db"
git add .gitattributes

# Add and commit database
git add kennel_inspections.db
git commit -m "Add database with LFS"
git push
```

### Option 2: Create a Demo Database (Faster)
```bash
# Create smaller demo with 500 kennels
python3 << 'EOF'
import sqlite3
import shutil

# Backup original
shutil.copy('kennel_inspections.db', 'kennel_inspections_FULL.db')

conn = sqlite3.connect('kennel_inspections.db')
c = conn.cursor()

# Get first 500 kennels
c.execute("SELECT id FROM kennels LIMIT 500")
kennel_ids = [str(row[0]) for row in c.fetchall()]
id_list = ','.join(kennel_ids)

# Delete kennels beyond first 500
c.execute(f"DELETE FROM kennels WHERE id NOT IN ({id_list})")
c.execute(f"DELETE FROM inspections WHERE kennel_id NOT IN ({id_list})")
c.execute("DELETE FROM inspection_items WHERE inspection_id NOT IN (SELECT id FROM inspections)")
c.execute("DELETE FROM dog_counts WHERE inspection_id NOT IN (SELECT id FROM inspections)")

conn.commit()
conn.execute("VACUUM")  # Shrink database file
conn.close()
print("✓ Demo database created (500 kennels)")
EOF

# Check new size
ls -lh kennel_inspections.db

# Commit and push
git add kennel_inspections.db
git commit -m "Demo database for deployment"
git push
```

## Then Deploy to Render

1. Go to https://render.com
2. Sign in with GitHub
3. Click **"New +" → "Web Service"**
4. Select your repository
5. Accept defaults (render.yaml configures everything)
6. Click **"Create Web Service"**
7. Wait 2-5 minutes
8. Visit your app at: `https://pa-kennel-inspections.onrender.com`

## That's it! 🚀

Your kennel inspection browser will be live and accessible to anyone with the URL.

**Free tier includes:**
- 750 hours/month uptime
- Custom subdomain with HTTPS
- Automatic deploys on git push

**Note:** App spins down after 15 min of inactivity. First request after sleeping takes ~30 seconds to wake up.
