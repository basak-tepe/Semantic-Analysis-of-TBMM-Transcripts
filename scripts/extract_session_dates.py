#!/usr/bin/env python3
"""
Script to extract session dates from TBMM transcript files.
Converts dates from various formats to DD.MM.YYYY format.
Creates a lookup CSV for session_date conversion.
"""

import os
import re
import csv
from pathlib import Path
from collections import defaultdict


def extract_date_from_header(content):
    """
    Extract date from the first 8000 characters of a TXT file.
    Looks for patterns like "7.5.1943", "20 .1 .1988", or "3 1 . 1 0 . 2007".
    
    Returns the date in DD.MM.YYYY format or None if not found.
    """
    # Look only at first 8000 characters
    header = content[:8000]
    
    # First try: standard pattern (digits together)
    # Examples: "7.5.1943", "20 .1 .1988", "7 . 5 . 1943"
    pattern1 = r'\b(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{4})\b'
    
    matches = re.findall(pattern1, header)
    
    if matches:
        # Take the first match
        day, month, year = matches[0]
        
        # Convert to DD.MM.YYYY format (zero-padded)
        day = day.zfill(2)
        month = month.zfill(2)
        
        return f"{day}.{month}.{year}"
    
    # Second try: pattern with spaces within day/month digits
    # Examples: "3 1 . 1 0 . 2007", "2 3 . 1 0 . 2003"
    pattern2 = r'\b(\d)\s+(\d)\s*\.\s*(\d)\s+(\d)\s*\.\s*(\d{4})\b'
    
    matches = re.findall(pattern2, header)
    
    if matches:
        # Take the first match and reconstruct the date
        day1, day2, month1, month2, year = matches[0]
        
        # Build day and month
        day = day1 + day2
        month = month1 + month2
        
        # Convert to DD.MM.YYYY format (already 2 digits)
        return f"{day}.{month}.{year}"
    
    # Third try: pattern with spaces within all digits including year
    # Examples: "6 . 11 . 2 0 0 8", "2 3 . 1 0 . 2 0 0 3"
    pattern3 = r'\b(\d)\s*(\d)?\s*\.\s*(\d)\s*(\d)?\s*\.\s*(\d)\s+(\d)\s+(\d)\s+(\d)\b'
    
    matches = re.findall(pattern3, header)
    
    if matches:
        # Take the first match and reconstruct the date
        day1, day2, month1, month2, year1, year2, year3, year4 = matches[0]
        
        # Build day, month, and year
        day = (day1 + day2) if day2 else day1
        month = (month1 + month2) if month2 else month1
        year = year1 + year2 + year3 + year4
        
        # Convert to DD.MM.YYYY format
        day = day.zfill(2)
        month = month.zfill(2)
        
        return f"{day}.{month}.{year}"
    
    return None


def process_txts_folder(txts_dir):
    """
    Process all TXT files in the TXTs directory recursively.
    Excludes files ending with fih.txt or gnd.txt.
    
    Returns a dictionary with filename -> date mappings, list of files without dates, and statistics.
    """
    txts_path = Path(txts_dir)
    
    if not txts_path.exists():
        print(f"Error: Directory {txts_dir} does not exist")
        return None, None, None
    
    results = {}
    no_dates = []
    stats = defaultdict(int)
    
    # Iterate through all subdirectories
    for subdir in sorted(txts_path.iterdir()):
        if not subdir.is_dir():
            continue
        
        stats['total_subdirs'] += 1
        subdir_found = 0
        subdir_total = 0
        
        # Process all .txt files in this subdirectory
        for txt_file in sorted(subdir.glob("*.txt")):
            # Skip files ending with fih.txt or gnd.txt
            if txt_file.name.endswith("fih.txt") or txt_file.name.endswith("gnd.txt"):
                stats['excluded_files'] += 1
                continue
            
            subdir_total += 1
            stats['total_files'] += 1
            
            try:
                # Read file content
                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Extract date
                date = extract_date_from_header(content)
                
                if date:
                    results[txt_file.name] = date
                    stats['files_with_dates'] += 1
                    subdir_found += 1
                else:
                    no_dates.append(txt_file.name)
                    stats['files_without_dates'] += 1
                    
            except Exception as e:
                print(f"Error reading {txt_file}: {e}")
                stats['error_files'] += 1
        
        # Print stats for this subdirectory
        if subdir_total > 0:
            print(f"{subdir.name}: Found dates in {subdir_found}/{subdir_total} files")
    
    return results, no_dates, stats


def save_to_csv(results, output_file):
    """Save the filename -> date mappings to a CSV file."""
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['filename', 'session_date'])
        
        for filename in sorted(results.keys()):
            writer.writerow([filename, results[filename]])
    
    print(f"\nSaved results to {output_file}")


def save_no_dates_csv(no_dates, output_file):
    """Save the list of filenames without dates to a CSV file."""
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['filename'])
        
        for filename in sorted(no_dates):
            writer.writerow([filename])
    
    print(f"Saved files without dates to {output_file}")


def main():
    # Get the project root directory (parent of scripts folder)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    txts_dir = project_root / "TXTs"
    output_file = project_root / "session_dates_lookup.csv"
    no_dates_file = project_root / "session_dates_not_found.csv"
    
    print("=" * 70)
    print("Session Date Extraction Script")
    print("=" * 70)
    print(f"Scanning directory: {txts_dir}")
    print("Excluding files ending with: fih.txt, gnd.txt")
    print("Looking at first 8000 characters of each file")
    print("=" * 70)
    print()
    
    # Process all files
    results, no_dates, stats = process_txts_folder(txts_dir)
    
    if results is None:
        return
    
    # Save to CSV
    if results:
        save_to_csv(results, output_file)
    
    # Save files without dates
    if no_dates:
        save_no_dates_csv(no_dates, no_dates_file)
    
    # Print summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    print(f"Total subdirectories processed: {stats['total_subdirs']}")
    print(f"Total files scanned: {stats['total_files']}")
    print(f"Files with dates found: {stats['files_with_dates']}")
    print(f"Files without dates: {stats['files_without_dates']}")
    print(f"Excluded files (fih/gnd): {stats['excluded_files']}")
    print(f"Error reading files: {stats['error_files']}")
    print("=" * 70)
    
    if stats['files_with_dates'] > 0:
        success_rate = (stats['files_with_dates'] / stats['total_files']) * 100
        print(f"\nSuccess rate: {success_rate:.1f}%")
        print(f"\nExtracted dates from {stats['files_with_dates']} files")
    
    # Show some examples
    if results:
        print("\n" + "=" * 70)
        print("SAMPLE RESULTS (first 10)")
        print("=" * 70)
        for i, (filename, date) in enumerate(sorted(results.items())[:10]):
            print(f"{filename:<30} -> {date}")
        
        if len(results) > 10:
            print(f"... and {len(results) - 10} more")


if __name__ == "__main__":
    main()

