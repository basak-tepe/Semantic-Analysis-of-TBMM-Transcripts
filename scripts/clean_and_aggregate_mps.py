"""
Clean and Aggregate MP Data

1. Clean party names by removing text after "Partisi" or "Parti"
2. Create aggregated CSV with MPs as rows and terms as columns
"""

import csv
import os
import re
from collections import defaultdict
from typing import Dict, Set

# Paths
INPUT_FILE = "../data/mps_by_term.csv"
CLEANED_FILE = "../data/mps_by_term_cleaned.csv"
AGGREGATED_FILE = "../data/mps_aggregated_by_term.csv"


def clean_party_name(party: str) -> str:
    """
    Clean party name by removing text after 'Partisi' or 'Parti'.
    
    Examples:
        "Cumhuriyet Halk Partisi Extra Text" -> "Cumhuriyet Halk Partisi"
        "Adalet ve Kalkınma Partisi Foo Bar" -> "Adalet ve Kalkınma Partisi"
        "Demokrat Parti Something" -> "Demokrat Parti"
    
    Args:
        party: Raw party name
        
    Returns:
        Cleaned party name
    """
    if not party or party.strip() == "":
        return party
    
    party = party.strip()
    
    # Try to find "Partisi" first (more specific)
    match = re.search(r'^(.*?Partisi)\b', party, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # If not found, try "Parti" (less specific, catches "Demokrat Parti")
    match = re.search(r'^(.*?Parti)\b', party, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # If neither found, return original (might be independent or other label)
    return party


def clean_mps_by_term(input_file: str, output_file: str) -> int:
    """
    Clean the party names in mps_by_term.csv.
    
    Args:
        input_file: Path to input CSV
        output_file: Path to output CSV
        
    Returns:
        Number of records processed
    """
    print("=" * 80)
    print("CLEANING PARTY NAMES")
    print("=" * 80)
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print("=" * 80)
    
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return 0
    
    cleaned_count = 0
    unchanged_count = 0
    total_count = 0
    
    cleaned_examples = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as fin:
            with open(output_file, 'w', encoding='utf-8', newline='') as fout:
                reader = csv.DictReader(fin)
                writer = csv.DictWriter(fout, fieldnames=['term', 'mp_name', 'party'])
                writer.writeheader()
                
                for row in reader:
                    total_count += 1
                    original_party = row['party']
                    cleaned_party = clean_party_name(original_party)
                    
                    # Track changes
                    if original_party != cleaned_party:
                        cleaned_count += 1
                        if len(cleaned_examples) < 10:  # Save first 10 examples
                            cleaned_examples.append({
                                'original': original_party,
                                'cleaned': cleaned_party
                            })
                    else:
                        unchanged_count += 1
                    
                    writer.writerow({
                        'term': row['term'],
                        'mp_name': row['mp_name'],
                        'party': cleaned_party
                    })
        
        print(f"\n✅ Cleaned {total_count:,} records")
        print(f"   🔧 Modified: {cleaned_count:,}")
        print(f"   ✓ Unchanged: {unchanged_count:,}")
        
        if cleaned_examples:
            print(f"\n📋 Sample Changes (first 10):")
            for example in cleaned_examples:
                print(f"   Before: {example['original'][:60]}")
                print(f"   After:  {example['cleaned'][:60]}")
                print()
        
        return total_count
        
    except Exception as e:
        print(f"❌ Error cleaning data: {e}")
        return 0


def aggregate_by_mp(input_file: str, output_file: str) -> int:
    """
    Create aggregated CSV with MPs as rows and terms as columns.
    
    Args:
        input_file: Path to cleaned mps_by_term.csv
        output_file: Path to output aggregated CSV
        
    Returns:
        Number of unique MPs
    """
    print("\n" + "=" * 80)
    print("AGGREGATING BY MP")
    print("=" * 80)
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print("=" * 80)
    
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return 0
    
    # Data structure: {mp_name: {term: party}}
    mp_data: Dict[str, Dict[int, str]] = defaultdict(dict)
    all_terms: Set[int] = set()
    
    try:
        # Read data
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                mp_name = row['mp_name']
                term = int(row['term'])
                party = row['party']
                
                mp_data[mp_name][term] = party
                all_terms.add(term)
        
        # Sort MPs alphabetically and terms numerically
        sorted_mps = sorted(mp_data.keys())
        sorted_terms = sorted(all_terms)
        
        print(f"📊 Found {len(sorted_mps):,} unique MPs")
        print(f"📊 Covering {len(sorted_terms)} terms: {min(sorted_terms)}-{max(sorted_terms)}")
        
        # Write aggregated data
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            # Create column headers
            fieldnames = ['speech_giver'] + [f'term{term}' for term in sorted_terms]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write each MP
            for mp_name in sorted_mps:
                row_data = {'speech_giver': mp_name}
                
                for term in sorted_terms:
                    party = mp_data[mp_name].get(term, '')  # Empty if MP not in that term
                    row_data[f'term{term}'] = party
                
                writer.writerow(row_data)
        
        print(f"\n✅ Created aggregated file with {len(sorted_mps):,} MPs")
        print(f"   Columns: speech_giver, {', '.join([f'term{t}' for t in sorted_terms[:5]])}...")
        
        # Show sample data
        print(f"\n📋 Sample Data (first 3 MPs):")
        for mp_name in sorted_mps[:3]:
            terms_served = [str(term) for term, party in sorted(mp_data[mp_name].items()) if party]
            parties = list(set(mp_data[mp_name].values()))
            print(f"   {mp_name}")
            print(f"      Terms: {', '.join(terms_served)}")
            print(f"      Parties: {', '.join(parties)}")
        
        return len(sorted_mps)
        
    except Exception as e:
        print(f"❌ Error aggregating data: {e}")
        return 0


def main():
    """Main execution function."""
    print("\n" + "🔧" * 40)
    print("MP DATA CLEANING AND AGGREGATION")
    print("🔧" * 40)
    
    # Step 1: Clean party names
    cleaned_count = clean_mps_by_term(INPUT_FILE, CLEANED_FILE)
    
    if cleaned_count == 0:
        print("❌ Cleaning failed. Exiting.")
        return
    
    # Step 2: Create aggregated file
    mp_count = aggregate_by_mp(CLEANED_FILE, AGGREGATED_FILE)
    
    if mp_count == 0:
        print("❌ Aggregation failed.")
        return
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print("=" * 80)
    print(f"📄 Cleaned file: {CLEANED_FILE}")
    print(f"📄 Aggregated file: {AGGREGATED_FILE}")
    print(f"📊 Total records cleaned: {cleaned_count:,}")
    print(f"📊 Unique MPs: {mp_count:,}")
    print("=" * 80)
    
    # Show file locations
    print("\n💡 Next steps:")
    print(f"   1. Review cleaned data: {CLEANED_FILE}")
    print(f"   2. Use aggregated data: {AGGREGATED_FILE}")
    print(f"   3. Original data preserved: {INPUT_FILE}")


if __name__ == "__main__":
    main()
