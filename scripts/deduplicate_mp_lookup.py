#!/usr/bin/env python3
"""
MP Lookup Deduplication Script

This script cleans the mp_lookup.csv file by:
1. Creating a backup of the original file
2. Normalizing all MP names (removing apostrophes)
3. Identifying and merging duplicate entries
4. Selecting the most complete data for each MP
5. Generating a deduplication log

Usage:
    python scripts/deduplicate_mp_lookup.py
"""

import csv
import os
import sys
import ast
from datetime import datetime
from collections import defaultdict

# Add src directory to path to import the normalizer
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from mp_name_normalizer import (
    normalize_mp_name,
    is_valid_mp_name,
    contains_conjunction_words,
    group_similar_names,
    select_canonical_name,
    merge_mp_data
)


def load_mp_lookup(filepath):
    """
    Load MP lookup CSV file into a dictionary.
    
    Returns:
        Dictionary mapping speech_giver -> {party, terms}
    """
    mp_data = {}
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return mp_data
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse terms list safely
            try:
                terms = ast.literal_eval(row.get('terms', '[]'))
            except (ValueError, SyntaxError):
                terms = []
            
            mp_data[row['speech_giver']] = {
                'party': row.get('political_party', ''),
                'terms': terms
            }
    
    print(f"✅ Loaded {len(mp_data)} entries from {filepath}")
    return mp_data


def save_mp_lookup(filepath, mp_data):
    """
    Save MP data dictionary to CSV file.
    """
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['speech_giver', 'political_party', 'terms'])
        writer.writeheader()
        
        # Sort by speech_giver for consistency
        for name in sorted(mp_data.keys()):
            data = mp_data[name]
            writer.writerow({
                'speech_giver': name,
                'political_party': data.get('party', ''),
                'terms': data.get('terms', [])
            })
    
    print(f"💾 Saved {len(mp_data)} entries to {filepath}")


def create_backup(filepath):
    """
    Create a backup of the original file.
    
    Returns:
        Path to backup file
    """
    backup_path = filepath.replace('.csv', '_backup.csv')
    
    # If backup already exists, add timestamp
    if os.path.exists(backup_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = filepath.replace('.csv', f'_backup_{timestamp}.csv')
    
    # Copy file
    import shutil
    shutil.copy2(filepath, backup_path)
    
    print(f"💾 Backup created: {backup_path}")
    return backup_path


def normalize_all_names(mp_data):
    """
    Normalize all names in the MP data.
    
    Returns:
        Tuple of (normalized_data, normalization_map, direct_duplicates)
        - normalized_data: dict with normalized names as keys
        - normalization_map: dict mapping original -> normalized name  
        - direct_duplicates: dict mapping normalized_name -> list of original names
    """
    normalized_data = {}
    normalization_map = {}
    direct_duplicates = {}
    
    for original_name, data in mp_data.items():
        normalized_name = normalize_mp_name(original_name)
        normalization_map[original_name] = normalized_name
        
        # Track all originals that map to this normalized name
        if normalized_name not in direct_duplicates:
            direct_duplicates[normalized_name] = []
        direct_duplicates[normalized_name].append(original_name)
        
        # If normalized name already exists, merge the data
        if normalized_name in normalized_data:
            # Merge data: prefer non-empty values
            existing = normalized_data[normalized_name]
            
            # Merge party: keep non-empty
            if not existing.get('party') and data.get('party'):
                existing['party'] = data['party']
            
            # Merge terms: union of all terms
            existing_terms = set(existing.get('terms', []))
            new_terms = set(data.get('terms', []))
            existing['terms'] = sorted(list(existing_terms | new_terms))
        else:
            normalized_data[normalized_name] = data.copy()
    
    return normalized_data, normalization_map, direct_duplicates


def identify_problematic_names(normalized_data, max_length=45):
    """
    Identify names that are problematic (long or containing conjunctions).
    
    A name is problematic if:
    1. Length exceeds max_length (default: 45 characters)
    2. Contains "ve" or "ile" as separate words (compound names)
    
    Returns:
        List of (name, reason) tuples for problematic names
    """
    problematic = []
    
    for name in normalized_data.keys():
        reasons = []
        
        # Check length
        if len(name) > max_length:
            reasons.append(f"length={len(name)}")
        
        # Check for conjunction words
        if contains_conjunction_words(name):
            reasons.append("contains_conjunction")
        
        if reasons:
            reason_str = ", ".join(reasons)
            problematic.append((name, reason_str))
    
    return problematic


def deduplicate_mp_lookup(input_file, output_file, log_file, threshold=0.9):
    """
    Main deduplication function.
    
    Args:
        input_file: Path to input CSV
        output_file: Path to output CSV
        log_file: Path to deduplication log CSV
        threshold: Similarity threshold for fuzzy matching (default: 0.9)
    """
    print("\n" + "="*60)
    print("MP LOOKUP DEDUPLICATION")
    print("="*60 + "\n")
    
    # Step 1: Load data
    print("📂 Step 1: Loading MP lookup data...")
    mp_data = load_mp_lookup(input_file)
    original_count = len(mp_data)
    
    # Step 2: Create backup
    print("\n💾 Step 2: Creating backup...")
    backup_path = create_backup(input_file)
    
    # Step 3: Normalize names
    print("\n🔄 Step 3: Normalizing all names...")
    normalized_data, normalization_map, direct_duplicates = normalize_all_names(mp_data)
    
    # Count how many were normalized differently
    changed_by_normalization = sum(
        1 for orig, norm in normalization_map.items() 
        if orig != norm
    )
    print(f"   ✓ {changed_by_normalization} names changed by normalization")
    
    # Count direct duplicates (multiple originals → same normalized)
    direct_dup_count = sum(1 for variants in direct_duplicates.values() if len(variants) > 1)
    print(f"   ✓ {direct_dup_count} normalized names have multiple original variants")
    
    # Step 4: Identify problematic names
    print(f"\n⚠️  Step 4: Identifying problematic names (>45 chars or contains 've'/'ile')...")
    problematic = identify_problematic_names(normalized_data)
    if problematic:
        print(f"   ⚠️  Found {len(problematic)} problematic names:")
        for name, reason in problematic[:5]:  # Show first 5
            print(f"      - {name[:60]}... ({reason})")
        if len(problematic) > 5:
            print(f"      ... and {len(problematic) - 5} more")
    else:
        print("   ✓ No problematic names found")
    
    # Step 5: Group similar names
    print(f"\n🔍 Step 5: Finding similar names (threshold: {threshold})...")
    all_names = list(normalized_data.keys())
    groups = group_similar_names(all_names, normalized_data, threshold)
    
    # Count groups with duplicates
    duplicate_groups = {k: v for k, v in groups.items() if v}
    print(f"   ✓ Found {len(duplicate_groups)} groups with duplicates")
    
    # Step 6: Merge duplicates
    print("\n🔗 Step 6: Merging duplicate entries...")
    merged_data = {}
    merge_log = []
    
    # First, log direct duplicates from normalization
    for normalized_name, original_names in direct_duplicates.items():
        if len(original_names) > 1:
            # Multiple originals normalized to the same name
            canonical = original_names[0]  # Use first as canonical
            for variant in original_names[1:]:
                merge_log.append({
                    'original_name': variant,
                    'canonical_name': canonical,
                    'reason': 'direct_normalization',
                    'original_party': mp_data[variant].get('party', ''),
                    'original_terms': str(mp_data[variant].get('terms', [])),
                    'merged_party': normalized_data[normalized_name].get('party', ''),
                    'merged_terms': str(normalized_data[normalized_name].get('terms', []))
                })
    
    # Then process fuzzy match groups
    for canonical_name, variants in groups.items():
        if not variants:
            # No duplicates, keep as is
            merged_data[canonical_name] = normalized_data[canonical_name]
        else:
            # Merge data from variants
            merged = merge_mp_data(canonical_name, variants, normalized_data)
            merged_data[canonical_name] = merged
            
            # Log the merge
            for variant in variants:
                merge_log.append({
                    'original_name': variant,
                    'canonical_name': canonical_name,
                    'reason': 'fuzzy_match',
                    'original_party': normalized_data[variant].get('party', ''),
                    'original_terms': str(normalized_data[variant].get('terms', [])),
                    'merged_party': merged.get('party', ''),
                    'merged_terms': str(merged.get('terms', []))
                })
    
    print(f"   ✓ Merged {len(merge_log)} duplicate entries")
    
    # Step 7: Save results
    print("\n💾 Step 7: Saving deduplicated data...")
    save_mp_lookup(output_file, merged_data)
    
    # Step 8: Save merge log
    print("\n📝 Step 8: Saving deduplication log...")
    with open(log_file, 'w', encoding='utf-8', newline='') as f:
        if merge_log:
            writer = csv.DictWriter(f, fieldnames=[
                'original_name', 'canonical_name', 'reason',
                'original_party', 'original_terms',
                'merged_party', 'merged_terms'
            ])
            writer.writeheader()
            writer.writerows(merge_log)
            print(f"   ✓ Saved {len(merge_log)} merge operations to {log_file}")
        else:
            writer = csv.writer(f)
            writer.writerow(['message'])
            writer.writerow(['No duplicates found - no merges performed'])
            print(f"   ℹ️  No duplicates found")
    
    # Summary
    print("\n" + "="*60)
    print("DEDUPLICATION SUMMARY")
    print("="*60)
    print(f"Original entries:     {original_count}")
    print(f"Deduplicated entries: {len(merged_data)}")
    print(f"Duplicates removed:   {original_count - len(merged_data)}")
    print(f"Reduction:            {((original_count - len(merged_data)) / original_count * 100):.1f}%")
    print(f"\nBackup saved to:      {backup_path}")
    print(f"Cleaned data saved to: {output_file}")
    print(f"Merge log saved to:    {log_file}")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Get the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, "data")
    
    # Define file paths
    input_file = os.path.join(project_root,data_dir, "mp_lookup.csv")
    output_file = os.path.join(project_root,data_dir, "mp_lookup.csv")  # Overwrite
    log_file = os.path.join(project_root,data_dir, "mp_deduplication_log.csv")
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Run deduplication
    try:
        deduplicate_mp_lookup(input_file, output_file, log_file, threshold=0.9)
        print("✅ Deduplication complete!")
    except Exception as e:
        print(f"\n❌ Error during deduplication: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
