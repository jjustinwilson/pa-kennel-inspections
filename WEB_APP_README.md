# 🌐 Web Application - Kennel Inspection Browser

## Overview

A Flask web application to browse and explore PA kennel inspection reports through an intuitive HTML interface.

## Features

### 📊 Dashboard
- Summary statistics (total kennels, inspections, violations)
- Quick search functionality
- Filter by county
- Show only kennels with violations

### 🔍 Search & Browse
- Search kennels by name or license number
- Filter by county
- View kennels with violation history
- See inspection counts and violation counts

### 🏢 Kennel Details
- Complete kennel information
- Full inspection history
- Dog count trends over time
- Violation summaries

### 📋 Inspection Reports
- Detailed inspection findings
- Dog counts (current and previous year)
- All inspection categories with results
- Color-coded violations (red for unsatisfactory)
- Inspector notes and remarks
- Reinspection requirements

### 🚨 Violations Page
- List of all violations
- Violation statistics by category
- Recent violations (last 500)
- Links to full inspection reports

## How to Run

### Start the Web Server

```bash
cd /Users/jjustinwilson/Desktop/kennel
source venv/bin/activate
python app.py
```

The server will start on: **http://localhost:5000**

### Open in Browser

```bash
open http://localhost:5000
```

Or visit manually: `http://localhost:5000`

## Pages

### Home Page (`/`)
- Dashboard with statistics
- Search form
- Quick links to violations and problem kennels

### Search Results (`/search`)
- List of kennels matching search criteria
- Shows license, county, inspection count, violation count
- Click kennel name to view details

### Kennel Detail (`/kennel/<id>`)
- Complete kennel information
- All inspections for that kennel
- Dog count trends
- Links to individual inspection reports

### Inspection Detail (`/inspection/<id>`)
- Full inspection report
- Dog counts (current/previous year)
- All inspection findings organized by section
- Color-coded results
- Inspector remarks

### Violations (`/violations`)
- Statistics on most common violations
- Recent 500 violations
- Filter and browse violation history

## Search Examples

### Find a Specific Kennel
```
Search: "Happy Paws"
Result: All kennels with "Happy Paws" in name
```

### Find Kennels in a County
```
County: LANCASTER
Result: All Lancaster County kennels
```

### Find Problem Kennels
```
☑ Show only kennels with violations
Result: Kennels with unsatisfactory findings
```

### Combined Search
```
Search: "Puppy"
County: YORK
☑ Show only kennels with violations
Result: York County kennels with "Puppy" in name that have violations
```

## API Endpoints

### Chart Data
```
GET /api/kennel/<kennel_id>/chart-data
Returns: JSON with dog count trends
```

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML, CSS (no JavaScript required)
- **Styling**: Custom CSS with responsive design

## File Structure

```
kennel/
├── app.py                      # Flask application
├── templates/
│   ├── base.html              # Base template
│   ├── index.html             # Home page
│   ├── search_results.html    # Search results
│   ├── kennel_detail.html     # Kennel details
│   ├── inspection_detail.html # Inspection report
│   └── violations.html        # Violations list
└── static/
    └── css/
        └── style.css          # Styling
```

## Features Explained

### Color Coding
- 🟢 **Green badges**: Satisfactory, Open status
- 🔴 **Red badges**: Unsatisfactory, Closed status
- 🟡 **Yellow badges**: Warnings, Reinspection required

### Inspection Results
- **Satisfactory**: No issues found
- **Unsatisfactory**: Violation found (highlighted in red)
- **Not Applicable**: Category doesn't apply
- **Yes/No**: Binary responses

### Dog Counts
Shows both current and previous year:
- Breeding dogs
- Boarding dogs
- Other dogs
- Transfer dogs
- On premises
- Off site

## Customization

### Change Port
Edit `app.py`:
```python
app.run(debug=True, port=8080)  # Change to desired port
```

### Limit Results
Search results limited to 100 kennels by default.
Edit in `app.py`:
```python
sql += " ORDER BY k.name LIMIT 100"  # Change limit
```

### Violations Display
Violations page shows last 500 by default.
Edit in `app.py`:
```python
LIMIT 500  # Change in violations() function
```

## Performance

- Fast searches with indexed database
- Efficient queries with proper JOINs
- Responsive design for mobile/tablet
- No heavy JavaScript frameworks

## Security Notes

- Read-only database access
- No user authentication (local use)
- SQL injection protected (parameterized queries)
- For production, add authentication and HTTPS

## Troubleshooting

### Port Already in Use
```bash
# Kill existing Flask process
pkill -f "python app.py"

# Or use different port
python app.py  # Edit port in app.py first
```

### Database Not Found
Make sure you're in the correct directory:
```bash
cd /Users/jjustinwilson/Desktop/kennel
ls kennel_inspections.db  # Should exist
```

### No Data Showing
Check if database has imported data:
```bash
python check_progress.py
```

### CSS Not Loading
Make sure directory structure is correct:
```bash
ls -R static/
# Should show: static/css/style.css
```

## Next Steps

### Add Features
- Export to CSV/PDF
- Advanced filtering
- Charts and graphs
- Email notifications for new violations

### Deploy
- Use production WSGI server (gunicorn)
- Add authentication
- Set up reverse proxy (nginx)
- Enable HTTPS

## Quick Commands

```bash
# Start server
python app.py

# Stop server
Ctrl+C

# Run in background
nohup python app.py &

# Check if running
ps aux | grep app.py

# View logs
tail -f nohup.out
```

## Example Queries

### Find All Lancaster Kennels
1. Go to home page
2. Select "LANCASTER" from county dropdown
3. Click Search

### View Recent Violations
1. Click "Recent Violations" on home page
2. Browse list of 500 most recent violations

### Check Specific Kennel
1. Search for kennel name
2. Click kennel name in results
3. View all inspections and details

## Summary

✅ **Simple and intuitive** web interface
✅ **No complex setup** - just run and browse
✅ **Responsive design** - works on all devices
✅ **Fast searches** - indexed database queries
✅ **Complete data** - all inspection details available

**Access at: http://localhost:5000** 🚀
