#!/usr/bin/env python3
"""
PA Department of Agriculture - Kennel Inspections PDF Scraper
Downloads all kennel inspection PDFs organized by county and kennel name.
Stores kennel details in SQLite database.
Runs with parallel workers and terminal UI.
"""

import os
import re
import sys
import time
import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import dataclass
from typing import Optional
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
from rich import print as rprint

BASE_URL = "https://www.pda.pa.gov"
SEARCH_URL = f"{BASE_URL}/PADogLawPublicKennelInspectionSearch/KennelInspections/Index/SearchForm"
OUTPUT_DIR = Path("kennel_inspections")
DB_FILE = "kennel_inspections.db"

# County mapping from the HTML dropdown (value -> name)
COUNTIES = {
    1: "ADAMS", 2: "ALLEGHENY", 3: "ARMSTRONG", 4: "BEAVER", 5: "BEDFORD",
    6: "BERKS", 7: "BLAIR", 8: "BRADFORD", 9: "BUCKS", 10: "BUTLER",
    11: "CAMBRIA", 12: "CAMERON", 13: "CARBON", 14: "CENTRE", 15: "CHESTER",
    16: "CLARION", 17: "CLEARFIELD", 18: "CLINTON", 19: "COLUMBIA", 20: "CRAWFORD",
    21: "CUMBERLAND", 22: "DAUPHIN", 23: "DELAWARE", 24: "ELK", 25: "ERIE",
    26: "FAYETTE", 27: "FOREST", 28: "FRANKLIN", 29: "FULTON", 30: "GREENE",
    31: "HUNTINGDON", 32: "INDIANA", 33: "JEFFERSON", 34: "JUNIATA", 35: "LACKAWANNA",
    36: "LANCASTER", 37: "LAWRENCE", 38: "LEBANON", 39: "LEHIGH", 40: "LUZERNE",
    41: "LYCOMING", 42: "MCKEAN", 43: "MERCER", 44: "MIFFLIN", 45: "MONROE",
    46: "MONTGOMERY", 47: "MONTOUR", 48: "NORTHAMPTON", 49: "NORTHUMBERLAND", 50: "PERRY",
    51: "PHILADELPHIA", 52: "PIKE", 53: "POTTER", 54: "SCHUYLKILL", 55: "SNYDER",
    56: "SOMERSET", 57: "SULLIVAN", 58: "SUSQUEHANNA", 59: "TIOGA", 60: "UNION",
    61: "VENANGO", 62: "WARREN", 63: "WASHINGTON", 64: "WAYNE", 65: "WESTMORELAND",
    66: "WYOMING", 67: "YORK", 68: "OUT-OF-STATE", 69: "UNKNOWN"
}


@dataclass
class KennelDetails:
    """Kennel information from details page."""
    kennel_id: int
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    county: str
    township: str
    license_number: str
    last_status: str
    last_issued_license_year: str
    last_license_class: str
    details_url: str


# Thread-safe locks
db_lock = Lock()
print_lock = Lock()
console = Console()


def log(message: str, style: str = ""):
    """Thread-safe logging with color."""
    with print_lock:
        if style:
            console.print(message, style=style)
        else:
            console.print(message)


def init_database():
    """Initialize SQLite database with schema."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kennels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kennel_id INTEGER UNIQUE,
            name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            county TEXT,
            township TEXT,
            license_number TEXT,
            last_status TEXT,
            last_issued_license_year TEXT,
            last_license_class TEXT,
            details_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kennel_id INTEGER,
            inspection_date TEXT,
            pdf_url TEXT,
            pdf_path TEXT,
            downloaded INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kennel_id) REFERENCES kennels(kennel_id),
            UNIQUE(kennel_id, inspection_date)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kennels_county ON kennels(county)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kennels_license ON kennels(license_number)')
    
    conn.commit()
    conn.close()


def save_kennel_to_db(kennel: KennelDetails):
    """Save kennel details to database."""
    with db_lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO kennels 
            (kennel_id, name, address, city, state, zip_code, county, township,
             license_number, last_status, last_issued_license_year, last_license_class, 
             details_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            kennel.kennel_id, kennel.name, kennel.address, kennel.city, 
            kennel.state, kennel.zip_code, kennel.county, kennel.township,
            kennel.license_number, kennel.last_status, kennel.last_issued_license_year,
            kennel.last_license_class, kennel.details_url
        ))
        
        conn.commit()
        conn.close()


def save_inspection_to_db(kennel_id: int, inspection_date: str, pdf_url: str, pdf_path: str, downloaded: bool):
    """Save inspection record to database."""
    with db_lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO inspections 
            (kennel_id, inspection_date, pdf_url, pdf_path, downloaded)
            VALUES (?, ?, ?, ?, ?)
        ''', (kennel_id, inspection_date, pdf_url, pdf_path, 1 if downloaded else 0))
        
        conn.commit()
        conn.close()


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = sanitized.strip(' .')
    return sanitized[:100] if len(sanitized) > 100 else sanitized


def create_session() -> requests.Session:
    """Create a requests session with appropriate headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    return session


def search_county(session: requests.Session, county_id: int) -> list[dict]:
    """Search for all kennels in a specific county."""
    kennels = []
    
    data = {
        'County': county_id,
        'KennelType': '',
        'LicenseNumber': '',
        'KennelName': '',
        'KennelPersonLastName': '',
        'KennelPersonFirstName': '',
        'City': '',
        'ZipCode': ''
    }
    
    try:
        response = session.post(SEARCH_URL, data=data, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='table')
        if not table:
            return kennels
        
        rows = table.find_all('tr')[1:]
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 5:
                license_num = cells[1].get_text(strip=True)
                kennel_info = cells[2].get_text(separator=' ', strip=True)
                status = cells[3].get_text(strip=True)
                
                details_link = cells[4].find('a')
                if details_link and details_link.get('href'):
                    details_url = urljoin(BASE_URL, details_link['href'])
                    kennel_name = kennel_info.split('\n')[0].split('  ')[0].strip()
                    kennel_id = int(details_link['href'].split('/')[-1])
                    
                    kennels.append({
                        'kennel_id': kennel_id,
                        'license_number': license_num,
                        'name': kennel_name,
                        'status': status,
                        'details_url': details_url,
                        'county_id': county_id,
                        'county_name': COUNTIES.get(county_id, f"County_{county_id}")
                    })
        
    except requests.RequestException as e:
        log(f"  [red]✗[/red] Error searching: {e}")
    
    return kennels


def parse_kennel_details(session: requests.Session, details_url: str, county_name: str) -> Optional[KennelDetails]:
    """Parse the kennel details page to extract all information."""
    try:
        response = session.get(details_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        kennel_id = int(details_url.split('/')[-1])
        
        details_div = soup.find('div', class_='container')
        if not details_div:
            return None
        
        text_content = details_div.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in text_content.split('\n') if l.strip()]
        
        name = ""
        address = ""
        city = ""
        state = "PA"
        zip_code = ""
        township = ""
        license_number = ""
        last_status = ""
        last_issued_year = ""
        last_license_class = ""
        
        kennel_section = soup.find('h4', string=re.compile('Kennel Inspections', re.I))
        if kennel_section:
            parent = kennel_section.find_parent()
            if parent:
                all_text = []
                for elem in parent.children:
                    if elem.name == 'table':
                        break
                    if hasattr(elem, 'get_text'):
                        all_text.append(elem.get_text(separator='\n', strip=True))
                    elif isinstance(elem, str) and elem.strip():
                        all_text.append(elem.strip())
                
                full_text = '\n'.join(all_text)
                lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line == 'KENNEL' and i + 1 < len(lines):
                name = lines[i + 1] if i + 1 < len(lines) else ""
                i += 2
                addr_parts = []
                while i < len(lines) and not lines[i].startswith('County:'):
                    addr_parts.append(lines[i])
                    i += 1
                if addr_parts:
                    address = addr_parts[0] if addr_parts else ""
                    if len(addr_parts) > 1:
                        last_addr = addr_parts[-1]
                        match = re.match(r'(.+?)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', last_addr)
                        if match:
                            city = match.group(1).strip()
                            state = match.group(2)
                            zip_code = match.group(3)
                continue
            
            if line.startswith('Township:'):
                township = line.replace('Township:', '').strip()
            
            if line == 'LICENSE NUMBER' and i + 1 < len(lines):
                for j in range(i + 1, min(i + 5, len(lines))):
                    if re.match(r'^\d+$', lines[j]):
                        license_number = lines[j]
                        break
            
            if line == 'LAST STATUS' and i + 1 < len(lines):
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j] in ['Open', 'Closed - Voluntarily', 'Closed - Enforcement Related', 
                                    'Application/License Refused', 'Closed - Non-Renewal']:
                        last_status = lines[j]
                        break
                    elif 'Closed' in lines[j] or 'Open' in lines[j]:
                        last_status = lines[j]
                        break
            
            if line == 'LAST ISSUED LICENSE YEAR' and i + 1 < len(lines):
                for j in range(i + 1, min(i + 5, len(lines))):
                    if re.match(r'^\d{4}$', lines[j]):
                        last_issued_year = lines[j]
                        break
            
            if line == 'LAST LICENSE CLASS' and i + 1 < len(lines):
                for j in range(i + 1, min(i + 5, len(lines))):
                    if re.match(r'^[A-Z]+\d*:', lines[j]) or 'dogs' in lines[j].lower():
                        last_license_class = lines[j]
                        break
            
            i += 1
        
        for line in lines:
            if line.startswith('County:'):
                county_from_page = line.replace('County:', '').strip()
                if county_from_page:
                    county_name = county_from_page
            if line.startswith('Township:'):
                township = line.replace('Township:', '').strip()
        
        return KennelDetails(
            kennel_id=kennel_id,
            name=name,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            county=county_name,
            township=township,
            license_number=license_number,
            last_status=last_status,
            last_issued_license_year=last_issued_year,
            last_license_class=last_license_class,
            details_url=details_url
        )
        
    except requests.RequestException:
        return None


def get_inspection_pdfs(session: requests.Session, details_url: str) -> list[dict]:
    """Get all inspection PDF links from a kennel details page."""
    pdfs = []
    
    try:
        response = session.get(details_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='table')
        if not table:
            return pdfs
        
        rows = table.find_all('tr')[1:]
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                date_cell = cells[1].get_text(strip=True)
                pdf_link = cells[2].find('a')
                if pdf_link and pdf_link.get('href'):
                    pdf_url = urljoin(BASE_URL, pdf_link['href'])
                    pdfs.append({
                        'date': date_cell,
                        'url': pdf_url
                    })
        
    except requests.RequestException:
        pass
    
    return pdfs


def download_pdf(session: requests.Session, url: str, filepath: Path) -> bool:
    """Download a PDF file to the specified path."""
    try:
        response = session.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
        
    except requests.RequestException:
        return False


class Stats:
    """Thread-safe statistics tracker."""
    def __init__(self):
        self.lock = Lock()
        self.kennels_found = 0
        self.pdfs_downloaded = 0
        self.pdfs_skipped = 0
        self.pdfs_failed = 0
    
    def add(self, kennels=0, downloaded=0, skipped=0, failed=0):
        with self.lock:
            self.kennels_found += kennels
            self.pdfs_downloaded += downloaded
            self.pdfs_skipped += skipped
            self.pdfs_failed += failed


def collect_all_kennels(start_county: int, end_county: int) -> list[dict]:
    """Collect all kennels from all counties first."""
    all_kennels = []
    session = create_session()
    
    console.print("\n[bold cyan]Phase 1:[/bold cyan] Collecting kennel list from all counties...\n")
    
    for county_id in range(start_county, end_county + 1):
        county_name = COUNTIES.get(county_id, f"County_{county_id}")
        console.print(f"  🔍 Searching [yellow]{county_name}[/yellow]...", end="")
        
        kennels = search_county(session, county_id)
        
        if kennels:
            all_kennels.extend(kennels)
            console.print(f" [green]Found {len(kennels)} kennels[/green]")
        else:
            console.print(f" [dim]No kennels[/dim]")
        
        time.sleep(0.3)
    
    console.print(f"\n[bold green]✓[/bold green] Total kennels found: [bold]{len(all_kennels)}[/bold]\n")
    return all_kennels


def process_kennel(worker_id: int, kennel: dict, progress: Progress, overall_task, stats: Stats, delay: float):
    """Process a single kennel - download its details and all PDFs."""
    session = create_session()
    county_name = kennel['county_name']
    
    # Create directory structure
    county_dir = OUTPUT_DIR / sanitize_filename(county_name)
    kennel_folder = f"{sanitize_filename(kennel['license_number'])}_{sanitize_filename(kennel['name'])}"
    kennel_dir = county_dir / kennel_folder
    kennel_dir.mkdir(parents=True, exist_ok=True)
    
    # Update progress
    progress.update(overall_task, description=f"[cyan]W{worker_id}[/cyan] 📥 {kennel['name'][:30]}...")
    
    time.sleep(delay)
    
    # Parse and save kennel details
    details = parse_kennel_details(session, kennel['details_url'], county_name)
    if details:
        save_kennel_to_db(details)
    
    # Get and download PDFs
    pdfs = get_inspection_pdfs(session, kennel['details_url'])
    
    kennel_downloaded = 0
    kennel_skipped = 0
    
    for pdf in pdfs:
        date_clean = pdf['date'].replace('/', '-')
        filename = f"inspection_{date_clean}.pdf"
        filepath = kennel_dir / filename
        
        if filepath.exists():
            save_inspection_to_db(kennel['kennel_id'], pdf['date'], pdf['url'], str(filepath), True)
            kennel_skipped += 1
            continue
        
        time.sleep(delay)
        
        if download_pdf(session, pdf['url'], filepath):
            kennel_downloaded += 1
            save_inspection_to_db(kennel['kennel_id'], pdf['date'], pdf['url'], str(filepath), True)
        else:
            stats.add(failed=1)
            save_inspection_to_db(kennel['kennel_id'], pdf['date'], pdf['url'], str(filepath), False)
    
    stats.add(kennels=1, downloaded=kennel_downloaded, skipped=kennel_skipped)
    progress.advance(overall_task)


def scrape_all_parallel(num_workers: int = 5, start_county: int = 1, end_county: int = 69, delay: float = 0.5):
    """Main scraping function with parallel workers and progress display."""
    
    # Initialize
    init_database()
    OUTPUT_DIR.mkdir(exist_ok=True)
    stats = Stats()
    
    total_counties = end_county - start_county + 1
    
    # Print header
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🐕 PA Kennel Inspection Scraper[/bold cyan]\n"
        f"Counties: {start_county}-{end_county} ({total_counties} total)\n"
        f"Workers: {num_workers} | Delay: {delay}s",
        border_style="cyan"
    ))
    
    # PHASE 1: Collect all kennels from all counties
    all_kennels = collect_all_kennels(start_county, end_county)
    
    if not all_kennels:
        console.print("[yellow]No kennels found to process.[/yellow]")
        return
    
    # PHASE 2: Process kennels in parallel
    console.print(f"[bold cyan]Phase 2:[/bold cyan] Processing {len(all_kennels)} kennels with {num_workers} workers...\n")
    
    kennel_index = 0
    kennel_lock = Lock()
    
    def get_next_kennel():
        nonlocal kennel_index
        with kennel_lock:
            if kennel_index < len(all_kennels):
                kennel = all_kennels[kennel_index]
                kennel_index += 1
                return kennel
            return None
    
    # Create progress display
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=False
    )
    
    with progress:
        # Create a task for each worker
        worker_tasks = {}
        for i in range(num_workers):
            task_id = progress.add_task(f"[cyan]W{i+1}[/cyan] Waiting...", total=1)
            worker_tasks[i] = task_id
        
        # Main overall progress
        overall_task = progress.add_task(
            "[bold magenta]Processing Kennels[/bold magenta]", 
            total=len(all_kennels)
        )
        
        def worker_task(worker_id: int):
            processed = 0
            while True:
                kennel = get_next_kennel()
                if kennel is None:
                    progress.update(
                        worker_tasks[worker_id], 
                        description=f"[green]W{worker_id+1} ✓ Done ({processed} kennels)[/green]"
                    )
                    break
                
                progress.update(
                    worker_tasks[worker_id],
                    description=f"[cyan]W{worker_id+1}[/cyan] {kennel['name'][:25]}..."
                )
                
                process_kennel(worker_id + 1, kennel, progress, overall_task, stats, delay)
                processed += 1
            
            return processed
        
        # Run workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_workers)]
            
            # Wait for all to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    log(f"[red]Worker error: {e}[/red]")
    
    # Print summary
    console.print()
    console.print(Panel(
        f"[bold green]✓ Scraping Complete![/bold green]\n\n"
        f"📊 [bold]Statistics:[/bold]\n"
        f"   Kennels processed: [cyan]{stats.kennels_found}[/cyan]\n"
        f"   PDFs downloaded: [green]{stats.pdfs_downloaded}[/green]\n"
        f"   PDFs skipped (existing): [yellow]{stats.pdfs_skipped}[/yellow]\n"
        f"   PDFs failed: [red]{stats.pdfs_failed}[/red]\n\n"
        f"💾 [bold]Output:[/bold]\n"
        f"   Database: [cyan]{DB_FILE}[/cyan]\n"
        f"   PDFs: [cyan]{OUTPUT_DIR}/[/cyan]",
        title="[bold]Summary[/bold]",
        border_style="green"
    ))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape PA Kennel Inspection PDFs')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers (default: 5)')
    parser.add_argument('--start', type=int, default=1, help='Starting county ID (1-69)')
    parser.add_argument('--end', type=int, default=69, help='Ending county ID (1-69)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests in seconds')
    parser.add_argument('--county', type=int, help='Scrape only a specific county ID')
    
    args = parser.parse_args()
    
    if args.county:
        scrape_all_parallel(
            num_workers=1,
            start_county=args.county, 
            end_county=args.county, 
            delay=args.delay
        )
    else:
        scrape_all_parallel(
            num_workers=args.workers,
            start_county=args.start, 
            end_county=args.end, 
            delay=args.delay
        )
