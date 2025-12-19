#!/usr/bin/env python3
"""
Flask Web Application for PA Kennel Inspection Reports
Browse kennels, inspections, and violations through a simple web interface.
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB_FILE = "kennel_inspections.db"


def get_db():
    """Get database connection with optimizations for low memory."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Memory optimizations for SQLite
    conn.execute("PRAGMA cache_size = -2000")  # 2MB cache instead of default
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA mmap_size = 0")  # Disable memory mapping
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@app.route('/')
def index():
    """Home page with kennel search."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get summary statistics
    cursor.execute("SELECT COUNT(*) FROM kennels")
    total_kennels = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inspections WHERE inspector_name IS NOT NULL")
    total_inspections = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inspection_items WHERE result = 'Unsatisfactory'")
    total_violations = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inspections WHERE reinspection_required = 1")
    total_reinspections = cursor.fetchone()[0]
    
    # Get counties for filter
    cursor.execute("SELECT DISTINCT county FROM kennels ORDER BY county")
    counties = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('index.html',
                         total_kennels=total_kennels,
                         total_inspections=total_inspections,
                         total_violations=total_violations,
                         total_reinspections=total_reinspections,
                         counties=counties)


@app.route('/search')
def search():
    """Search kennels."""
    query = request.args.get('q', '')
    county = request.args.get('county', '')
    violations_only = request.args.get('violations', '') == 'true'
    
    conn = get_db()
    cursor = conn.cursor()
    
    sql = """
        SELECT DISTINCT k.kennel_id, k.name, k.county, k.city, k.license_number,
               k.last_status,
               (SELECT COUNT(*) FROM inspections i WHERE i.kennel_id = k.kennel_id) as inspection_count,
               (SELECT COUNT(*) 
                FROM inspections i 
                JOIN inspection_items ii ON i.id = ii.inspection_id 
                WHERE i.kennel_id = k.kennel_id AND ii.result = 'Unsatisfactory') as violation_count
        FROM kennels k
        WHERE 1=1
    """
    params = []
    
    if query:
        sql += " AND (k.name LIKE ? OR k.license_number LIKE ?)"
        params.extend([f'%{query}%', f'%{query}%'])
    
    if county:
        sql += " AND k.county = ?"
        params.append(county)
    
    if violations_only:
        sql += """ AND EXISTS (
            SELECT 1 FROM inspections i 
            JOIN inspection_items ii ON i.id = ii.inspection_id 
            WHERE i.kennel_id = k.kennel_id AND ii.result = 'Unsatisfactory'
        )"""
    
    sql += " ORDER BY k.name LIMIT 100"
    
    cursor.execute(sql, params)
    kennels = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('search_results.html', kennels=kennels, query=query)


@app.route('/kennel/<int:kennel_id>')
def kennel_detail(kennel_id):
    """Kennel detail page with all inspections."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get kennel info
    cursor.execute("""
        SELECT * FROM kennels WHERE kennel_id = ?
    """, (kennel_id,))
    kennel = dict(cursor.fetchone() or {})
    
    if not kennel:
        conn.close()
        return "Kennel not found", 404
    
    # Get inspections
    cursor.execute("""
        SELECT i.*, 
               (SELECT COUNT(*) FROM inspection_items ii 
                WHERE ii.inspection_id = i.id AND ii.result = 'Unsatisfactory') as violation_count,
               (SELECT COUNT(*) FROM inspection_items ii 
                WHERE ii.inspection_id = i.id AND ii.result = 'Satisfactory') as satisfactory_count
        FROM inspections i
        WHERE i.kennel_id = ?
        ORDER BY i.inspection_date DESC
    """, (kennel_id,))
    inspections = [dict(row) for row in cursor.fetchall()]
    
    # Get dog count trends
    cursor.execute("""
        SELECT i.inspection_date, dc.year_type, dc.breeding, dc.boarding, dc.on_prem
        FROM inspections i
        JOIN dog_counts dc ON i.id = dc.inspection_id
        WHERE i.kennel_id = ? AND dc.year_type = 'current'
        ORDER BY i.inspection_date DESC
        LIMIT 20
    """, (kennel_id,))
    dog_counts = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('kennel_detail.html', 
                         kennel=kennel, 
                         inspections=inspections,
                         dog_counts=dog_counts)


@app.route('/inspection/<int:inspection_id>')
def inspection_detail(inspection_id):
    """Inspection detail page with all findings."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get inspection info
    cursor.execute("""
        SELECT i.*, k.name as kennel_name, k.county, k.license_number
        FROM inspections i
        JOIN kennels k ON i.kennel_id = k.kennel_id
        WHERE i.id = ?
    """, (inspection_id,))
    inspection = dict(cursor.fetchone() or {})
    
    if not inspection:
        conn.close()
        return "Inspection not found", 404
    
    # Get dog counts
    cursor.execute("""
        SELECT * FROM dog_counts WHERE inspection_id = ?
    """, (inspection_id,))
    dog_counts = {row['year_type']: dict(row) for row in cursor.fetchall()}
    
    # Get inspection items grouped by section
    cursor.execute("""
        SELECT * FROM inspection_items 
        WHERE inspection_id = ?
        ORDER BY category_section, category_code
    """, (inspection_id,))
    
    items_by_section = {}
    for row in cursor.fetchall():
        item = dict(row)
        section = item['category_section'] or 'Other'
        if section not in items_by_section:
            items_by_section[section] = []
        items_by_section[section].append(item)
    
    conn.close()
    
    return render_template('inspection_detail.html',
                         inspection=inspection,
                         dog_counts=dog_counts,
                         items_by_section=items_by_section)


@app.route('/violations')
def violations():
    """List all violations."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT k.name as kennel_name, k.county, k.license_number,
               i.inspection_date, i.inspection_action,
               ii.category_name, ii.category_code, ii.category_section,
               i.id as inspection_id, k.kennel_id
        FROM inspection_items ii
        JOIN inspections i ON ii.inspection_id = i.id
        JOIN kennels k ON i.kennel_id = k.kennel_id
        WHERE ii.result = 'Unsatisfactory'
        ORDER BY i.inspection_date DESC
        LIMIT 500
    """)
    
    violations = [dict(row) for row in cursor.fetchall()]
    
    # Get violation statistics
    cursor.execute("""
        SELECT category_name, COUNT(*) as count
        FROM inspection_items
        WHERE result = 'Unsatisfactory'
        GROUP BY category_name
        ORDER BY count DESC
        LIMIT 20
    """)
    
    violation_stats = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('violations.html', 
                         violations=violations,
                         violation_stats=violation_stats)


@app.route('/api/kennel/<int:kennel_id>/chart-data')
def kennel_chart_data(kennel_id):
    """Get dog count data for charts."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT i.inspection_date, dc.breeding, dc.boarding, dc.on_prem, dc.transfer
        FROM inspections i
        JOIN dog_counts dc ON i.id = dc.inspection_id
        WHERE i.kennel_id = ? AND dc.year_type = 'current'
        ORDER BY i.inspection_date
    """, (kennel_id,))
    
    data = {
        'dates': [],
        'breeding': [],
        'boarding': [],
        'on_prem': [],
        'transfer': []
    }
    
    for row in cursor.fetchall():
        data['dates'].append(row['inspection_date'])
        data['breeding'].append(row['breeding'])
        data['boarding'].append(row['boarding'])
        data['on_prem'].append(row['on_prem'])
        data['transfer'].append(row['transfer'])
    
    conn.close()
    
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
