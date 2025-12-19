#!/usr/bin/env python3
"""
Import all PA Kennel Inspection PDFs into SQLite Database
Processes all inspection PDFs and extracts structured data.
"""

import sys
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from pdf_parser import parse_inspection_pdf
from db_importer import update_database_schema, import_inspection, get_import_stats, is_inspection_already_imported
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
    MofNCompleteColumn
)
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

DB_FILE = "kennel_inspections.db"
INSPECTIONS_DIR = Path("kennel_inspections")

console = Console()


def process_single_pdf(pdf_path_str):
    """Process a single PDF file - designed to be called by parallel workers."""
    try:
        pdf_path = Path(pdf_path_str)
        inspection_data = parse_inspection_pdf(str(pdf_path))
        return ('success', pdf_path_str, inspection_data)
    except Exception as e:
        return ('error', pdf_path_str, str(e))


def main(start_index=None, end_index=None, update_schema=True, num_workers=1, skip_existing=False):
    """Main import process."""
    
    # Print header
    console.print()
    batch_info = ""
    if start_index is not None or end_index is not None:
        batch_info = f"\nBatch: {start_index or 0} to {end_index or 'end'}"
    
    worker_info = f"\nWorkers: {num_workers} parallel" if num_workers > 1 else ""
    skip_info = "\nMode: Skip already imported" if skip_existing else ""
    
    console.print(Panel.fit(
        "[bold cyan]📄 PA Kennel Inspection PDF Importer[/bold cyan]\n"
        f"Database: {DB_FILE}\n"
        f"Source: {INSPECTIONS_DIR}/{batch_info}{worker_info}{skip_info}",
        border_style="cyan"
    ))
    console.print()
    
    # Step 1: Update database schema
    if update_schema:
        console.print("[bold]Step 1:[/bold] Updating database schema...")
        try:
            update_database_schema(DB_FILE)
            console.print("[green]✓[/green] Schema updated successfully\n")
        except Exception as e:
            console.print(f"[red]✗ Error updating schema: {e}[/red]")
            return 1
    else:
        console.print("[bold]Step 1:[/bold] Skipping schema update (--no-schema)\n")
    
    # Step 2: Collect all PDF files
    console.print("[bold]Step 2:[/bold] Collecting PDF files...")
    pdf_files = sorted(list(INSPECTIONS_DIR.glob("**/inspection_*.pdf")))
    
    if not pdf_files:
        console.print("[yellow]No PDF files found![/yellow]")
        return 1
    
    total_files = len(pdf_files)
    
    # Apply batch range
    if start_index is not None or end_index is not None:
        start = start_index or 0
        end = end_index or len(pdf_files)
        pdf_files = pdf_files[start:end]
        console.print(f"[green]✓[/green] Processing batch: {start:,} to {end:,} ({len(pdf_files):,} files) of {total_files:,} total\n")
    else:
        console.print(f"[green]✓[/green] Found {len(pdf_files):,} PDF files\n")
    
    # Step 3: Process PDFs
    console.print("[bold]Step 3:[/bold] Processing PDFs...\n")
    
    success_count = 0
    error_count = 0
    skip_count = 0
    already_imported_count = 0
    errors = []
    
    # Pre-filter PDFs if skip_existing is enabled
    if skip_existing:
        console.print("[cyan]Checking which PDFs are already imported...[/cyan]")
        original_count = len(pdf_files)
        pdf_files = [pdf for pdf in pdf_files if not is_inspection_already_imported(DB_FILE, str(pdf))]
        already_imported_count = original_count - len(pdf_files)
        if already_imported_count > 0:
            console.print(f"[green]✓[/green] Skipping {already_imported_count:,} already imported PDFs")
            console.print(f"[cyan]Processing {len(pdf_files):,} remaining PDFs[/cyan]\n")
        
        if len(pdf_files) == 0:
            console.print("[green]All PDFs in this range are already imported![/green]")
            console.print(Panel(
                "[bold green]✓ Nothing to import![/bold green]\n\n"
                "All PDFs in the specified range have already been imported.",
                border_style="green"
            ))
            return 0
    
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn("[cyan]{task.fields[current_file]}[/cyan]"),
        console=console,
        expand=False
    )
    
    if num_workers > 1:
        # Parallel processing mode
        console.print(f"[cyan]Using {num_workers} parallel workers[/cyan]\n")
        
        with progress:
            task = progress.add_task(
                "[cyan]Processing PDFs...[/cyan]",
                total=len(pdf_files),
                current_file=""
            )
            
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                # Submit all PDF parsing jobs
                future_to_pdf = {
                    executor.submit(process_single_pdf, str(pdf)): pdf 
                    for pdf in pdf_files
                }
                
                processed = 0
                for future in as_completed(future_to_pdf):
                    pdf_path = future_to_pdf[future]
                    
                    try:
                        status, pdf_str, result = future.result()
                        
                        if status == 'success':
                            inspection_data = result
                            if inspection_data:
                                # Import to database (sequential for SQLite safety)
                                success = import_inspection(DB_FILE, inspection_data, pdf_str)
                                if success:
                                    success_count += 1
                                else:
                                    skip_count += 1
                            else:
                                skip_count += 1
                        else:
                            error_count += 1
                            errors.append((pdf_str, result))
                            if len(errors) > 10:
                                errors.pop(0)
                        
                    except Exception as e:
                        error_count += 1
                        errors.append((str(pdf_path), str(e)))
                        if len(errors) > 10:
                            errors.pop(0)
                    
                    processed += 1
                    
                    # Update progress
                    if processed % 10 == 0:
                        progress.update(
                            task,
                            description=f"[cyan]Processing[/cyan]",
                            current_file=f"{pdf_path.parent.name[:25]}/{pdf_path.name[:25]}"
                        )
                    
                    progress.advance(task)
                    
                    # Print status update every 500 files
                    if processed % 500 == 0:
                        console.print(f"[dim]  Checkpoint: {processed:,}/{len(pdf_files):,} processed ({success_count:,} imported)[/dim]")
    
    else:
        # Sequential processing mode (original)
        with progress:
            task = progress.add_task(
                "[cyan]Processing PDFs...[/cyan]",
                total=len(pdf_files),
                current_file=""
            )
            
            for i, pdf_path in enumerate(pdf_files):
                try:
                    # Update progress with current file every 10 files
                    if i % 10 == 0:
                        progress.update(
                            task,
                            description=f"[cyan]Processing[/cyan]",
                            current_file=f"{pdf_path.parent.name[:25]}/{pdf_path.name[:25]}"
                        )
                    
                    # Parse PDF
                    inspection_data = parse_inspection_pdf(str(pdf_path))
                    
                    if inspection_data:
                        # Import to database
                        success = import_inspection(DB_FILE, inspection_data, str(pdf_path))
                        if success:
                            success_count += 1
                        else:
                            skip_count += 1
                    else:
                        skip_count += 1
                    
                    progress.advance(task)
                    
                    # Print status update every 500 files
                    if (i + 1) % 500 == 0:
                        console.print(f"[dim]  Checkpoint: {i+1:,}/{len(pdf_files):,} processed ({success_count:,} imported)[/dim]")
                    
                except Exception as e:
                    error_count += 1
                    errors.append((str(pdf_path), str(e)))
                    progress.advance(task)
                    
                    # Only keep last 10 errors to avoid memory issues
                    if len(errors) > 10:
                        errors.pop(0)
    
    # Step 4: Show results
    console.print()
    console.print("[bold]Step 4:[/bold] Import complete!\n")
    
    # Get database statistics
    stats = get_import_stats(DB_FILE)
    
    # Create results table
    table = Table(title="Import Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")
    
    if skip_existing:
        table.add_row("PDFs in Range", f"{len(pdf_files) + already_imported_count:,}")
        table.add_row("Already Imported (skipped)", f"{already_imported_count:,}")
        table.add_row("PDFs Processed", f"{len(pdf_files):,}")
    else:
        table.add_row("PDFs Processed", f"{len(pdf_files):,}")
    table.add_row("Successfully Imported", f"{success_count:,}")
    table.add_row("Skipped (no match)", f"{skip_count:,}")
    table.add_row("Errors", f"{error_count:,}")
    table.add_row("", "")
    table.add_row("Inspections with Metadata", f"{stats['inspections_with_metadata']:,}")
    table.add_row("Inspections with Dog Counts", f"{stats['inspections_with_dog_counts']:,}")
    table.add_row("Inspections with Items", f"{stats['inspections_with_items']:,}")
    table.add_row("Total Inspection Items", f"{stats['total_inspection_items']:,}")
    table.add_row("Violations Found", f"{stats['violations']:,}")
    table.add_row("Reinspections Required", f"{stats['reinspections_required']:,}")
    
    console.print(table)
    console.print()
    
    # Show sample errors if any
    if errors:
        console.print("[yellow]Sample Errors (last 10):[/yellow]")
        for pdf_path, error in errors[-10:]:
            console.print(f"  [red]✗[/red] {Path(pdf_path).name}: {error[:80]}")
        console.print()
    
    # Final summary
    console.print(Panel(
        f"[bold green]✓ Import Complete![/bold green]\n\n"
        f"Successfully imported data from [cyan]{success_count:,}[/cyan] PDFs\n"
        f"Database: [cyan]{DB_FILE}[/cyan]",
        border_style="green"
    ))
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Import PA Kennel Inspection PDFs into SQLite database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all PDFs (single worker)
  python import_pdfs.py
  
  # Import with 8 parallel workers (3-5x faster!)
  python import_pdfs.py --workers 8
  
  # Import first 1000 PDFs with parallel processing
  python import_pdfs.py --start 0 --end 1000 --workers 8
  
  # Import next batch (1000-2000)
  python import_pdfs.py --start 1000 --end 2000 --no-schema --workers 8
  
  # Resume from file 5000 with 4 workers
  python import_pdfs.py --start 5000 --workers 4
  
  # Skip already imported PDFs (fast resume)
  python import_pdfs.py --start 0 --workers 8 --skip-existing
        """
    )
    
    parser.add_argument('--start', type=int, default=None,
                        help='Start index (0-based) for batch processing')
    parser.add_argument('--end', type=int, default=None,
                        help='End index (exclusive) for batch processing')
    parser.add_argument('--no-schema', action='store_true',
                        help='Skip schema update (useful for subsequent batches)')
    parser.add_argument('--workers', type=int, default=1,
                        help='Number of parallel workers (default: 1, use 4-8 for speed)')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip PDFs that have already been imported (faster for re-runs)')
    
    args = parser.parse_args()
    
    try:
        sys.exit(main(
            start_index=args.start,
            end_index=args.end,
            update_schema=not args.no_schema,
            num_workers=args.workers,
            skip_existing=args.skip_existing
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Import interrupted by user[/yellow]")
        console.print("[dim]You can resume with: python import_pdfs.py --start <last_processed> --no-schema[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
