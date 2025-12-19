#!/usr/bin/env python3
"""Check import progress and database statistics."""

import sqlite3
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

DB_FILE = "kennel_inspections.db"
INSPECTIONS_DIR = Path("kennel_inspections")

console = Console()

def main():
    # Count total PDFs
    total_pdfs = len(list(INSPECTIONS_DIR.glob("**/inspection_*.pdf")))
    
    # Get database stats
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Count imported inspections
    cursor.execute("SELECT COUNT(*) FROM inspections WHERE inspector_name IS NOT NULL")
    imported = cursor.fetchone()[0]
    
    # Get detailed stats
    cursor.execute("SELECT COUNT(DISTINCT inspection_id) FROM dog_counts")
    with_dog_counts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT inspection_id) FROM inspection_items")
    with_items = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inspection_items")
    total_items = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inspection_items WHERE result = 'Unsatisfactory'")
    violations = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM inspections WHERE reinspection_required = 1")
    reinspections = cursor.fetchone()[0]
    
    # Top violators
    cursor.execute("""
        SELECT k.name, k.county, COUNT(*) as violation_count
        FROM kennels k
        JOIN inspections i ON k.kennel_id = i.kennel_id
        JOIN inspection_items ii ON i.id = ii.inspection_id
        WHERE ii.result = 'Unsatisfactory'
        GROUP BY k.kennel_id
        ORDER BY violation_count DESC
        LIMIT 10
    """)
    top_violators = cursor.fetchall()
    
    # Most common violations
    cursor.execute("""
        SELECT ii.category_name, COUNT(*) as count
        FROM inspection_items ii
        WHERE ii.result = 'Unsatisfactory'
        GROUP BY ii.category_name
        ORDER BY count DESC
        LIMIT 10
    """)
    common_violations = cursor.fetchall()
    
    conn.close()
    
    # Calculate progress
    progress_pct = (imported / total_pdfs * 100) if total_pdfs > 0 else 0
    remaining = total_pdfs - imported
    
    # Display results
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]📊 Import Progress Report[/bold cyan]\n"
        f"Database: {DB_FILE}",
        border_style="cyan"
    ))
    console.print()
    
    # Progress table
    table = Table(title="Import Progress", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Details", style="dim")
    
    table.add_row("Total PDFs", f"{total_pdfs:,}", "")
    table.add_row("Imported", f"{imported:,}", f"{progress_pct:.1f}% complete")
    table.add_row("Remaining", f"{remaining:,}", "")
    table.add_row("", "", "")
    table.add_row("With Dog Counts", f"{with_dog_counts:,}", "")
    table.add_row("With Inspection Items", f"{with_items:,}", "")
    table.add_row("Total Items", f"{total_items:,}", "")
    table.add_row("Violations", f"{violations:,}", "Unsatisfactory items")
    table.add_row("Reinspections Required", f"{reinspections:,}", "")
    
    console.print(table)
    console.print()
    
    # Top violators
    if top_violators:
        table2 = Table(title="Top 10 Kennels by Violation Count", show_header=True)
        table2.add_column("Kennel", style="yellow", width=40)
        table2.add_column("County", style="cyan")
        table2.add_column("Violations", justify="right", style="red")
        
        for name, county, count in top_violators:
            table2.add_row(name[:40], county, str(count))
        
        console.print(table2)
        console.print()
    
    # Common violations
    if common_violations:
        table3 = Table(title="Top 10 Most Common Violations", show_header=True)
        table3.add_column("Category", style="yellow", width=50)
        table3.add_column("Count", justify="right", style="red")
        
        for category, count in common_violations:
            table3.add_row(category[:50], str(count))
        
        console.print(table3)
        console.print()
    
    # Next steps
    if remaining > 0:
        console.print(Panel(
            f"[yellow]Import in progress[/yellow]\n\n"
            f"To continue importing:\n"
            f"  [cyan]python import_pdfs.py --start {imported} --no-schema[/cyan]\n\n"
            f"Or use batch runner:\n"
            f"  [cyan]./run_batch_import.sh {imported}[/cyan]",
            title="Next Steps",
            border_style="yellow"
        ))
    else:
        console.print(Panel(
            f"[green]✓ Import Complete![/green]\n\n"
            f"All {total_pdfs:,} PDFs have been imported successfully!",
            title="Status",
            border_style="green"
        ))

if __name__ == "__main__":
    main()
