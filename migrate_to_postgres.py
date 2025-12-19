#!/usr/bin/env python3
"""
Migrate SQLite database to PostgreSQL for Render deployment.
This script reads from kennel_inspections_FULL.db and populates the PostgreSQL database.
"""

import sqlite3
import psycopg2
import psycopg2.extras
import os
import sys
from datetime import datetime

# Database files
SQLITE_DB = "kennel_inspections_FULL.db"
POSTGRES_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost/pakenneldb')

def create_schema(pg_conn):
    """Create PostgreSQL tables with same schema as SQLite."""
    print("Creating PostgreSQL schema...")
    cursor = pg_conn.cursor()
    
    # Create kennels table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kennels (
            kennel_id INTEGER PRIMARY KEY,
            name TEXT,
            license_number TEXT,
            county TEXT,
            city TEXT,
            last_status TEXT,
            last_inspection_date TEXT,
            pdf_path TEXT
        )
    """)
    
    # Create inspections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inspections (
            id SERIAL PRIMARY KEY,
            kennel_id INTEGER NOT NULL,
            inspection_date TEXT,
            pdf_path TEXT,
            inspector_name TEXT,
            inspection_type TEXT,
            inspection_action TEXT,
            reinspection_required BOOLEAN DEFAULT FALSE,
            followup_date TEXT,
            license_expires TEXT,
            remarks TEXT,
            FOREIGN KEY (kennel_id) REFERENCES kennels(kennel_id)
        )
    """)
    
    # Create dog_counts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dog_counts (
            id SERIAL PRIMARY KEY,
            inspection_id INTEGER NOT NULL,
            year_type TEXT NOT NULL,
            breeding INTEGER,
            boarding INTEGER,
            on_prem INTEGER,
            transfer INTEGER,
            FOREIGN KEY (inspection_id) REFERENCES inspections(id),
            UNIQUE(inspection_id, year_type)
        )
    """)
    
    # Create inspection_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inspection_items (
            id SERIAL PRIMARY KEY,
            inspection_id INTEGER NOT NULL,
            category_name TEXT,
            category_code TEXT,
            category_section TEXT,
            result TEXT,
            FOREIGN KEY (inspection_id) REFERENCES inspections(id)
        )
    """)
    
    # Create indices for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kennels_county ON kennels(county)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kennels_name ON kennels(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspections_kennel ON inspections(kennel_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspections_date ON inspections(inspection_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspection_items_result ON inspection_items(result)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dog_counts_inspection ON dog_counts(inspection_id)")
    
    pg_conn.commit()
    print("✓ Schema created")

def migrate_kennels(sqlite_conn, pg_conn):
    """Migrate kennels table."""
    print("Migrating kennels...")
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    sqlite_cursor.execute("SELECT COUNT(*) FROM kennels")
    total = sqlite_cursor.fetchone()[0]
    print(f"  Total kennels to migrate: {total}")
    
    sqlite_cursor.execute("""
        SELECT kennel_id, name, license_number, county, city, 
               last_status, last_inspection_date, pdf_path
        FROM kennels
    """)
    
    batch_size = 1000
    batch = []
    count = 0
    
    for row in sqlite_cursor:
        batch.append(row)
        count += 1
        
        if len(batch) >= batch_size:
            psycopg2.extras.execute_batch(pg_cursor, """
                INSERT INTO kennels (kennel_id, name, license_number, county, city,
                                   last_status, last_inspection_date, pdf_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (kennel_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    license_number = EXCLUDED.license_number,
                    county = EXCLUDED.county,
                    city = EXCLUDED.city,
                    last_status = EXCLUDED.last_status,
                    last_inspection_date = EXCLUDED.last_inspection_date,
                    pdf_path = EXCLUDED.pdf_path
            """, batch)
            pg_conn.commit()
            print(f"  Migrated {count}/{total} kennels...")
            batch = []
    
    # Insert remaining
    if batch:
        psycopg2.extras.execute_batch(pg_cursor, """
            INSERT INTO kennels (kennel_id, name, license_number, county, city,
                               last_status, last_inspection_date, pdf_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (kennel_id) DO UPDATE SET
                name = EXCLUDED.name,
                license_number = EXCLUDED.license_number,
                county = EXCLUDED.county,
                city = EXCLUDED.city,
                last_status = EXCLUDED.last_status,
                last_inspection_date = EXCLUDED.last_inspection_date,
                pdf_path = EXCLUDED.pdf_path
        """, batch)
        pg_conn.commit()
    
    print(f"✓ Migrated {count} kennels")

def migrate_inspections(sqlite_conn, pg_conn):
    """Migrate inspections table."""
    print("Migrating inspections...")
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # Get mapping of old IDs to new IDs
    id_mapping = {}
    
    sqlite_cursor.execute("SELECT COUNT(*) FROM inspections WHERE inspector_name IS NOT NULL")
    total = sqlite_cursor.fetchone()[0]
    print(f"  Total inspections to migrate: {total}")
    
    sqlite_cursor.execute("""
        SELECT id, kennel_id, inspection_date, pdf_path, inspector_name,
               inspection_type, inspection_action, reinspection_required,
               followup_date, license_expires, remarks
        FROM inspections
        WHERE inspector_name IS NOT NULL
        ORDER BY id
    """)
    
    batch_size = 1000
    count = 0
    
    for row in sqlite_cursor:
        old_id = row[0]
        pg_cursor.execute("""
            INSERT INTO inspections (kennel_id, inspection_date, pdf_path, inspector_name,
                                   inspection_type, inspection_action, reinspection_required,
                                   followup_date, license_expires, remarks)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, row[1:])
        new_id = pg_cursor.fetchone()[0]
        id_mapping[old_id] = new_id
        count += 1
        
        if count % batch_size == 0:
            pg_conn.commit()
            print(f"  Migrated {count}/{total} inspections...")
    
    pg_conn.commit()
    print(f"✓ Migrated {count} inspections")
    return id_mapping

def migrate_dog_counts(sqlite_conn, pg_conn, id_mapping):
    """Migrate dog_counts table."""
    print("Migrating dog counts...")
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    sqlite_cursor.execute("""
        SELECT inspection_id, year_type, breeding, boarding, on_prem, transfer
        FROM dog_counts
        WHERE inspection_id IN (SELECT id FROM inspections WHERE inspector_name IS NOT NULL)
    """)
    
    batch = []
    count = 0
    
    for row in sqlite_cursor:
        old_inspection_id = row[0]
        if old_inspection_id in id_mapping:
            new_inspection_id = id_mapping[old_inspection_id]
            batch.append((new_inspection_id,) + row[1:])
            count += 1
            
            if len(batch) >= 1000:
                psycopg2.extras.execute_batch(pg_cursor, """
                    INSERT INTO dog_counts (inspection_id, year_type, breeding, boarding, on_prem, transfer)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (inspection_id, year_type) DO NOTHING
                """, batch)
                pg_conn.commit()
                print(f"  Migrated {count} dog count records...")
                batch = []
    
    if batch:
        psycopg2.extras.execute_batch(pg_cursor, """
            INSERT INTO dog_counts (inspection_id, year_type, breeding, boarding, on_prem, transfer)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (inspection_id, year_type) DO NOTHING
        """, batch)
        pg_conn.commit()
    
    print(f"✓ Migrated {count} dog count records")

def migrate_inspection_items(sqlite_conn, pg_conn, id_mapping):
    """Migrate inspection_items table."""
    print("Migrating inspection items...")
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    sqlite_cursor.execute("""
        SELECT inspection_id, category_name, category_code, category_section, result
        FROM inspection_items
        WHERE inspection_id IN (SELECT id FROM inspections WHERE inspector_name IS NOT NULL)
    """)
    
    batch = []
    count = 0
    
    for row in sqlite_cursor:
        old_inspection_id = row[0]
        if old_inspection_id in id_mapping:
            new_inspection_id = id_mapping[old_inspection_id]
            batch.append((new_inspection_id,) + row[1:])
            count += 1
            
            if len(batch) >= 1000:
                psycopg2.extras.execute_batch(pg_cursor, """
                    INSERT INTO inspection_items (inspection_id, category_name, category_code, category_section, result)
                    VALUES (%s, %s, %s, %s, %s)
                """, batch)
                pg_conn.commit()
                print(f"  Migrated {count} inspection items...")
                batch = []
    
    if batch:
        psycopg2.extras.execute_batch(pg_cursor, """
            INSERT INTO inspection_items (inspection_id, category_name, category_code, category_section, result)
            VALUES (%s, %s, %s, %s, %s)
        """, batch)
        pg_conn.commit()
    
    print(f"✓ Migrated {count} inspection items")

def main():
    """Main migration function."""
    print(f"\n{'='*60}")
    print("SQLite to PostgreSQL Migration")
    print(f"{'='*60}\n")
    print(f"Source: {SQLITE_DB}")
    print(f"Target: {POSTGRES_URL}\n")
    
    if not os.path.exists(SQLITE_DB):
        print(f"ERROR: SQLite database '{SQLITE_DB}' not found!")
        sys.exit(1)
    
    try:
        # Connect to both databases
        print("Connecting to databases...")
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        pg_conn = psycopg2.connect(POSTGRES_URL)
        print("✓ Connected\n")
        
        # Create schema
        create_schema(pg_conn)
        print()
        
        # Migrate tables
        migrate_kennels(sqlite_conn, pg_conn)
        print()
        
        id_mapping = migrate_inspections(sqlite_conn, pg_conn)
        print()
        
        migrate_dog_counts(sqlite_conn, pg_conn, id_mapping)
        print()
        
        migrate_inspection_items(sqlite_conn, pg_conn, id_mapping)
        print()
        
        # Close connections
        sqlite_conn.close()
        pg_conn.close()
        
        print(f"{'='*60}")
        print("✓ Migration completed successfully!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n ERROR: Migration failed!")
        print(f"  {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
