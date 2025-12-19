#!/usr/bin/env python3
"""
PDF Parser for PA Kennel Inspection Reports
Extracts structured data from inspection PDFs using pdftotext.
"""

import subprocess
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class InspectionData:
    """Structured data extracted from a kennel inspection PDF."""
    # Header fields
    kennel_name: str = ""
    owner_name: str = ""
    license_number: str = ""
    license_year_class: str = ""
    county: str = ""
    township: str = ""
    
    # Inspection metadata
    inspection_date: str = ""
    inspector_name: str = ""
    person_interviewed: str = ""
    person_title: str = ""
    inspection_action: str = ""
    
    # Dog counts
    curr_year_counts: Dict[str, int] = field(default_factory=dict)
    prev_year_counts: Dict[str, int] = field(default_factory=dict)
    
    # Inspection items
    inspection_items: List[Dict[str, str]] = field(default_factory=list)
    
    # Remarks
    remarks: str = ""
    reinspection_required: bool = False


def extract_pdf_text(pdf_path: str) -> str:
    """Use pdftotext to extract text from PDF."""
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', pdf_path, '-'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except Exception:
        return ""


def extract_field_value(text: str, field_name: str, lines: List[str]) -> str:
    """Extract value for a specific field from lines."""
    for i, line in enumerate(lines):
        if field_name in line:
            # Try to get value from same line first
            parts = line.split(field_name, 1)
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
            # Otherwise check next line
            if i + 1 < len(lines):
                return lines[i + 1].strip()
    return ""


def parse_dog_counts(lines: List[str]) -> tuple:
    """Parse dog counts section into current and previous year counts."""
    curr_counts = {
        'boarding': 0,
        'breeding': 0,
        'other': 0,
        'transfer': 0,
        'on_prem': 0,
        'off_site': 0
    }
    prev_counts = {
        'boarding': 0,
        'breeding': 0,
        'other': 0,
        'transfer': 0,
        'on_prem': 0,
        'off_site': 0
    }
    
    in_dog_counts = False
    for i, line in enumerate(lines):
        if 'Dog Counts' in line:
            in_dog_counts = True
            continue
        
        if in_dog_counts:
            # Look for current year counts
            if 'CurrYr: Boarding' in line or 'CurrYr:Boarding' in line:
                # Extract numbers from this and following lines
                for j in range(i, min(i + 10, len(lines))):
                    check_line = lines[j]
                    
                    # CurrYr: Boarding
                    if 'CurrYr: Breeding' in check_line or 'CurrYr:Breeding' in check_line:
                        match = re.search(r'(\d+)', check_line)
                        if match:
                            curr_counts['breeding'] = int(match.group(1))
                    elif 'CurrYr: Other' in check_line or 'CurrYr:Other' in check_line:
                        match = re.search(r'(\d+)', check_line)
                        if match:
                            curr_counts['other'] = int(match.group(1))
                    elif 'CurrYr: Transfer' in check_line or 'CurrYr:Transfer' in check_line:
                        match = re.search(r'(\d+)', check_line)
                        if match:
                            curr_counts['transfer'] = int(match.group(1))
                    elif 'On Prem' in check_line:
                        match = re.search(r'(\d+)', check_line)
                        if match:
                            curr_counts['on_prem'] = int(match.group(1))
                    elif 'Off Site' in check_line:
                        match = re.search(r'(\d+)', check_line)
                        if match:
                            curr_counts['off_site'] = int(match.group(1))
                    
                    # PrevYr counts
                    if 'PrevYr: Boarding' in check_line or 'PrevYr:Boarding' in check_line:
                        match = re.search(r'(\d+)', check_line)
                        if match:
                            prev_counts['boarding'] = int(match.group(1))
                    elif 'PrevYr: Breeding' in check_line or 'PrevYr:Breeding' in check_line:
                        match = re.search(r'(\d+)', check_line)
                        if match:
                            prev_counts['breeding'] = int(match.group(1))
                    elif 'PrevYr: Other' in check_line or 'PrevYr:Other' in check_line:
                        match = re.search(r'(\d+)', check_line)
                        if match:
                            prev_counts['other'] = int(match.group(1))
                    elif 'PrevYr: Transfer' in check_line or 'PrevYr:Transfer' in check_line:
                        match = re.search(r'(\d+)', check_line)
                        if match:
                            prev_counts['transfer'] = int(match.group(1))
                    
                    # Check for CurrYr: Boarding value on same line
                    if ('CurrYr: Boarding' in check_line or 'CurrYr:Boarding' in check_line) and j == i:
                        match = re.search(r'(\d+)', check_line)
                        if match:
                            curr_counts['boarding'] = int(match.group(1))
                
                break
            
            # Stop when we hit the next section
            if 'Kennel Regulations' in line or 'Inspection Category' in line:
                break
    
    return curr_counts, prev_counts


def parse_inspection_items(lines: List[str]) -> List[Dict[str, str]]:
    """Parse inspection category items with their results."""
    items = []
    current_section = None
    
    for i, line in enumerate(lines):
        # Detect section headers
        if 'Kennel Regulations' in line:
            current_section = 'Kennel Regulations'
            continue
        elif 'Kennel Acts' in line:
            current_section = 'Kennel Acts'
            continue
        elif 'Miscellaneous' in line and 'Inspection Category' in lines[i-1] if i > 0 else False:
            current_section = 'Miscellaneous'
            continue
        
        if not current_section:
            continue
        
        # Stop at Remarks section
        if 'Remarks' in line and i > 0 and 'Inspection Category' not in line:
            break
        
        # Parse category lines - look for patterns like "21.28a Food" or "455.8 Rabies Vaccination"
        # Results are typically on the same line or next line
        
        # Pattern 1: Code + Name on same line
        code_match = re.match(r'^(\d+\.?\d*[a-z]?\.?\d*)\s+(.+)$', line.strip())
        if code_match and current_section:
            code = code_match.group(1)
            name = code_match.group(2).strip()
            
            # Look for result on this line or next
            result = ""
            # Check if result is on same line (after enough spaces)
            parts = line.split()
            if len(parts) >= 3:
                potential_result = parts[-1]
                if potential_result in ['Satisfactory', 'Unsatisfactory', 'Yes', 'No', 'Not']:
                    if potential_result == 'Not' and i + 1 < len(lines) and 'Applicable' in lines[i + 1]:
                        result = 'Not Applicable'
                    else:
                        result = potential_result
                    # Remove result from name if it was included
                    name = ' '.join(parts[:-1]).replace(code, '').strip()
            
            # Check next line for result if not found
            if not result and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line in ['Satisfactory', 'Unsatisfactory', 'Yes', 'No', 'Not Applicable']:
                    result = next_line
            
            if result:
                items.append({
                    'section': current_section,
                    'code': code,
                    'name': name,
                    'result': result
                })
        
        # Pattern 2: Name with Result on same line (like "Other Satisfactory")
        elif current_section and line.strip():
            parts = line.strip().split()
            if len(parts) >= 2:
                potential_result = parts[-1]
                if potential_result in ['Satisfactory', 'Unsatisfactory', 'Yes', 'No']:
                    name = ' '.join(parts[:-1])
                    items.append({
                        'section': current_section,
                        'code': '',
                        'name': name,
                        'result': potential_result
                    })
                elif potential_result == 'Not' and 'Applicable' in line:
                    name = ' '.join(parts[:-2])
                    items.append({
                        'section': current_section,
                        'code': '',
                        'name': name,
                        'result': 'Not Applicable'
                    })
    
    return items


def parse_remarks(lines: List[str]) -> tuple:
    """Parse remarks section and check for reinspection requirement."""
    remarks_lines = []
    in_remarks = False
    reinspection_required = False
    
    for i, line in enumerate(lines):
        if 'Remarks' in line and not in_remarks:
            in_remarks = True
            # Skip the "Remarks" header line and any action lines
            continue
        
        if in_remarks:
            # Collect all text after Remarks
            remarks_lines.append(line)
            
            # Check for reinspection requirement
            if 'reinspection' in line.lower() or 're-inspection' in line.lower():
                if 'required' in line.lower() or 'will take place' in line.lower():
                    reinspection_required = True
    
    remarks = '\n'.join(remarks_lines).strip()
    return remarks, reinspection_required


def parse_inspection_pdf(pdf_path: str) -> Optional[InspectionData]:
    """Parse inspection PDF and return structured data."""
    text = extract_pdf_text(pdf_path)
    if not text:
        return None
    
    lines = text.split('\n')
    data = InspectionData()
    
    # Parse header information
    for i, line in enumerate(lines):
        # Kennel name (appears after "Kennel" and before "Owner(s)")
        if line.strip() == 'Kennel' and i + 1 < len(lines):
            # Skip to Owner(s) line and extract kennel name
            for j in range(i + 1, min(i + 10, len(lines))):
                if 'Owner(s)' in lines[j]:
                    # Kennel name is between "Kennel" and "Owner(s)"
                    # It might be on multiple lines
                    kennel_lines = []
                    for k in range(i + 1, j):
                        if lines[k].strip():
                            kennel_lines.append(lines[k].strip())
                    if kennel_lines:
                        data.kennel_name = ' '.join(kennel_lines)
                    break
        
        # Owner name
        if 'Owner(s)' in line:
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and 'PA' not in lines[j] and 'Business' not in lines[j]:
                    data.owner_name = lines[j].strip()
                    break
        
        # License number
        if 'License Number' in line:
            data.license_number = extract_field_value(text, 'License Number', lines)
        
        # License year/class
        if 'License Year/Class' in line:
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and ':' in lines[j]:
                    data.license_year_class = lines[j].strip()
                    break
        
        # County
        if 'Kennel County' in line:
            data.county = extract_field_value(text, 'Kennel County', lines)
        
        # Township
        if 'Kennel Township' in line:
            data.township = extract_field_value(text, 'Kennel Township', lines)
        
        # Inspection date
        if 'Inspection Date' in line:
            date_val = extract_field_value(text, 'Inspection Date', lines)
            # Clean up date - remove "Inspected By" if it got included
            if 'Inspected By' in date_val:
                date_val = date_val.split('Inspected By')[0].strip()
            data.inspection_date = date_val
        
        # Inspector name
        if 'Inspected By' in line:
            # Inspector name format: "LAST , FIRST" or "Last , First"
            # It might be on the same line after "Inspected By"
            if ',' in line:
                parts = line.split('Inspected By')
                if len(parts) > 1:
                    data.inspector_name = parts[1].strip()
            else:
                for j in range(i + 1, min(i + 5, len(lines))):
                    if ',' in lines[j]:
                        data.inspector_name = lines[j].strip()
                        break
        
        # Person interviewed
        if 'Person Interviewed' in line:
            data.person_interviewed = extract_field_value(text, 'Person Interviewed', lines)
        
        # Person title
        if line.strip() == 'Title':
            if i + 1 < len(lines):
                data.person_title = lines[i + 1].strip()
        
        # Inspection action
        if 'Inspection Action' in line:
            data.inspection_action = extract_field_value(text, 'Inspection Action', lines)
    
    # Parse dog counts
    data.curr_year_counts, data.prev_year_counts = parse_dog_counts(lines)
    
    # Parse inspection items
    data.inspection_items = parse_inspection_items(lines)
    
    # Parse remarks
    data.remarks, data.reinspection_required = parse_remarks(lines)
    
    # Check for reinspection in miscellaneous items as well
    for item in data.inspection_items:
        if 'reinspection' in item.get('name', '').lower():
            if item.get('result', '').lower() == 'yes':
                data.reinspection_required = True
    
    return data


if __name__ == "__main__":
    # Test with a sample PDF
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        data = parse_inspection_pdf(pdf_path)
        if data:
            print(f"Kennel: {data.kennel_name}")
            print(f"Owner: {data.owner_name}")
            print(f"License: {data.license_number}")
            print(f"Date: {data.inspection_date}")
            print(f"Inspector: {data.inspector_name}")
            print(f"Action: {data.inspection_action}")
            print(f"\nCurrent Year Counts: {data.curr_year_counts}")
            print(f"Previous Year Counts: {data.prev_year_counts}")
            print(f"\nInspection Items: {len(data.inspection_items)} found")
            for item in data.inspection_items[:5]:
                print(f"  - {item}")
            print(f"\nReinspection Required: {data.reinspection_required}")
            print(f"\nRemarks (first 200 chars): {data.remarks[:200]}")
        else:
            print("Failed to parse PDF")
