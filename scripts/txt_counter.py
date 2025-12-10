#!/usr/bin/env python3
"""
Script to count text files in the TXTs folder.
Excludes files ending with 'fih.txt' or 'gnd.txt'.
"""

import os
from pathlib import Path


def count_txt_files(txts_dir):
    """
    Count .txt files in the TXTs directory, excluding those ending with fih.txt or gnd.txt.
    
    Args:
        txts_dir: Path to the TXTs directory
        
    Returns:
        dict: Dictionary with counts by subdirectory and total count
    """
    txts_path = Path(txts_dir)
    
    if not txts_path.exists():
        print(f"Error: Directory {txts_dir} does not exist")
        return None
    
    total_count = 0
    excluded_count = 0
    dir_counts = {}
    
    # Iterate through all subdirectories
    for subdir in sorted(txts_path.iterdir()):
        if subdir.is_dir():
            count = 0
            excluded = 0
            
            # Count .txt files in this subdirectory
            for txt_file in subdir.glob("*.txt"):
                if txt_file.name.endswith("fih.txt") or txt_file.name.endswith("gnd.txt"):
                    excluded += 1
                else:
                    count += 1
            
            if count > 0 or excluded > 0:
                dir_counts[subdir.name] = {
                    'count': count,
                    'excluded': excluded
                }
                total_count += count
                excluded_count += excluded
    
    return {
        'total': total_count,
        'excluded': excluded_count,
        'by_directory': dir_counts
    }


def main():
    # Get the project root directory (parent of scripts folder)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    txts_dir = project_root / "TXTs"
    
    print("=" * 70)
    print("TXT File Counter")
    print("=" * 70)
    print(f"Scanning directory: {txts_dir}")
    print("Excluding files ending with: fih.txt, gnd.txt")
    print("=" * 70)
    print()
    
    results = count_txt_files(txts_dir)
    
    if results is None:
        return
    
    # Print results by directory
    print(f"{'Directory':<20} {'Valid TXTs':<15} {'Excluded':<15}")
    print("-" * 70)
    
    for dir_name, counts in results['by_directory'].items():
        print(f"{dir_name:<20} {counts['count']:<15} {counts['excluded']:<15}")
    
    print("=" * 70)
    print(f"{'TOTAL':<20} {results['total']:<15} {results['excluded']:<15}")
    print("=" * 70)
    print()
    print(f"Summary:")
    print(f"  - Valid TXT files: {results['total']}")
    print(f"  - Excluded files: {results['excluded']}")
    print(f"  - Grand total: {results['total'] + results['excluded']}")
    print()


if __name__ == "__main__":
    main()

