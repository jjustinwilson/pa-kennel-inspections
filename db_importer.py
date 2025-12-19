#!/usr/bin/env python3
"""
Database Importer for PA Kennel Inspection Data
Manages schema updates and imports parsed inspection data into SQLite.
"""

import sqlite3
from typing import Optional
from pdf_parser import InspectionData


def update_database_schema(db_path: str):
    """Add new columns and tables to existing database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns already exist before adding them
    cursor.execute("PRAGMA table_info(inspections)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # Add new columns to inspections table if they don't exist
    new_columns = {
        'inspector_name': 'TEXT',
        'person_interviewed': 'TEXT',
        'person_title': 'TEXT',
        'inspection_action': 'TEXT',
        'license_year_class': 'TEXT',
        'remarks_text': 'TEXT',
        'reinspection_required': 'INTEGER DEFAULT 0'
    }
    
    for column_name, column_type in new_columns.items():
        if column_name not in existing_columns:
            try:
                cursor.execute(f'ALTER TABLE inspections ADD COLUMN {column_name} {column_type}')
                print(f"Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' not in str(e).lower():
                    raise
    
    # Create dog_counts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dog_counts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspection_id INTEGER NOT NULL,
            year_type TEXT NOT NULL,
            boarding INTEGER DEFAULT 0,
            breeding INTEGER DEFAULT 0,
            other_count INTEGER DEFAULT 0,
            transfer INTEGER DEFAULT 0,
            on_prem INTEGER DEFAULT 0,
            off_site INTEGER DEFAULT 0,
            FOREIGN KEY (inspection_id) REFERENCES inspections(id),
            UNIQUE(inspection_id, year_type)
        )
    ''')
    
    # Create inspection_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inspection_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspection_id INTEGER NOT NULL,
            category_section TEXT,
            category_code TEXT,
            category_name TEXT,
            result TEXT,
            FOREIGN KEY (inspection_id) REFERENCES inspections(id)
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dog_counts_inspection ON dog_counts(inspection_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_inspection_items_inspection ON inspection_items(inspection_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_inspection_items_result ON inspection_items(result)')
    
    conn.commit()
    conn.close()
    print("Database schema updated successfully")


def get_inspection_id_by_path(cursor: sqlite3.Cursor, pdf_path: str) -> Optional[int]:
    """Get inspection ID by PDF path."""
    cursor.execute('SELECT id FROM inspections WHERE pdf_path = ?', (pdf_path,))
    result = cursor.fetchone()
    return result[0] if result else None


def get_inspection_id_by_kennel_date(cursor: sqlite3.Cursor, kennel_id: int, inspection_date: str) -> Optional[int]:
    """Get inspection ID by kennel ID and date."""
    cursor.execute(
        'SELECT id FROM inspections WHERE kennel_id = ? AND inspection_date = ?',
        (kennel_id, inspection_date)
    )
    result = cursor.fetchone()
    return result[0] if result else None


def get_kennel_id_by_license(cursor: sqlite3.Cursor, license_number: str) -> Optional[int]:
    """Get kennel ID by license number."""
    if not license_number:
        return None
    cursor.execute('SELECT kennel_id FROM kennels WHERE license_number = ?', (license_number,))
    result = cursor.fetchone()
    return result[0] if result else None


def update_inspection_metadata(cursor: sqlite3.Cursor, inspection_id: int, data: InspectionData):
    """Update inspection record with parsed metadata."""
    cursor.execute('''
        UPDATE inspections
        SET inspector_name = ?,
            person_interviewed = ?,
            person_title = ?,
            inspection_action = ?,
            license_year_class = ?,
            remarks_text = ?,
            reinspection_required = ?
        WHERE id = ?
    ''', (
        data.inspector_name,
        data.person_interviewed,
        data.person_title,
        data.inspection_action,
        data.license_year_class,
        data.remarks,
        1 if data.reinspection_required else 0,
        inspection_id
    ))


def insert_dog_counts(cursor: sqlite3.Cursor, inspection_id: int, data: InspectionData):
    """Insert dog count records for current and previous years."""
    # Delete existing counts for this inspection (in case of re-import)
    cursor.execute('DELETE FROM dog_counts WHERE inspection_id = ?', (inspection_id,))
    
    # Insert current year counts
    cursor.execute('''
        INSERT OR REPLACE INTO dog_counts
        (inspection_id, year_type, boarding, breeding, other_count, transfer, on_prem, off_site)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        inspection_id,
        'current',
        data.curr_year_counts.get('boarding', 0),
        data.curr_year_counts.get('breeding', 0),
        data.curr_year_counts.get('other', 0),
        data.curr_year_counts.get('transfer', 0),
        data.curr_year_counts.get('on_prem', 0),
        data.curr_year_counts.get('off_site', 0)
    ))
    
    # Insert previous year counts
    cursor.execute('''
        INSERT OR REPLACE INTO dog_counts
        (inspection_id, year_type, boarding, breeding, other_count, transfer, on_prem, off_site)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        inspection_id,
        'previous',
        data.prev_year_counts.get('boarding', 0),
        data.prev_year_counts.get('breeding', 0),
        data.prev_year_counts.get('other', 0),
        data.prev_year_counts.get('transfer', 0),
        data.prev_year_counts.get('on_prem', 0),
        data.prev_year_counts.get('off_site', 0)
    ))


def insert_inspection_items(cursor: sqlite3.Cursor, inspection_id: int, data: InspectionData):
    """Insert inspection category items."""
    # Delete existing items for this inspection (in case of re-import)
    cursor.execute('DELETE FROM inspection_items WHERE inspection_id = ?', (inspection_id,))
    
    # Insert all inspection items
    for item in data.inspection_items:
        cursor.execute('''
            INSERT INTO inspection_items
            (inspection_id, category_section, category_code, category_name, result)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            inspection_id,
            item.get('section', ''),
            item.get('code', ''),
            item.get('name', ''),
            item.get('result', '')
        ))


def is_inspection_already_imported(db_path: str, pdf_path: str) -> bool:
    """Check if a PDF has already been imported (has metadata)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT inspector_name FROM inspections 
        WHERE pdf_path = ? AND inspector_name IS NOT NULL
    ''', (pdf_path,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None


def import_inspection(db_path: str, inspection_data: InspectionData, pdf_path: str) -> bool:
    """Import parsed inspection data into database."""
    if not inspection_data:
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Find inspection ID by PDF path first
        inspection_id = get_inspection_id_by_path(cursor, pdf_path)
        
        # If not found by path, try to find by kennel and date
        if not inspection_id and inspection_data.license_number and inspection_data.inspection_date:
            kennel_id = get_kennel_id_by_license(cursor, inspection_data.license_number)
            if kennel_id:
                inspection_id = get_inspection_id_by_kennel_date(
                    cursor,
                    kennel_id,
                    inspection_data.inspection_date
                )
        
        if not inspection_id:
            # Can't find or create inspection record - skip this file
            conn.close()
            return False
        
        # Update inspection metadata
        update_inspection_metadata(cursor, inspection_id, inspection_data)
        
        # Insert dog counts
        insert_dog_counts(cursor, inspection_id, inspection_data)
        
        # Insert inspection items
        insert_inspection_items(cursor, inspection_id, inspection_data)
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def get_import_stats(db_path: str) -> dict:
    """Get statistics on imported data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    stats = {}
    
    # Count inspections with metadata
    cursor.execute('SELECT COUNT(*) FROM inspections WHERE inspector_name IS NOT NULL')
    stats['inspections_with_metadata'] = cursor.fetchone()[0]
    
    # Count dog counts
    cursor.execute('SELECT COUNT(DISTINCT inspection_id) FROM dog_counts')
    stats['inspections_with_dog_counts'] = cursor.fetchone()[0]
    
    # Count inspection items
    cursor.execute('SELECT COUNT(*) FROM inspection_items')
    stats['total_inspection_items'] = cursor.fetchone()[0]
    
    # Count unique inspections with items
    cursor.execute('SELECT COUNT(DISTINCT inspection_id) FROM inspection_items')
    stats['inspections_with_items'] = cursor.fetchone()[0]
    
    # Count inspections requiring reinspection
    cursor.execute('SELECT COUNT(*) FROM inspections WHERE reinspection_required = 1')
    stats['reinspections_required'] = cursor.fetchone()[0]
    
    # Count violations (unsatisfactory items)
    cursor.execute("SELECT COUNT(*) FROM inspection_items WHERE result = 'Unsatisfactory'")
    stats['violations'] = cursor.fetchone()[0]
    
    conn.close()
    return stats


if __name__ == "__main__":
    # Test schema update
    import sys
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        print(f"Updating schema for: {db_path}")
        update_database_schema(db_path)
        
        stats = get_import_stats(db_path)
        print("\nCurrent database stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    else:
        print("Usage: python db_importer.py <database_path>")
