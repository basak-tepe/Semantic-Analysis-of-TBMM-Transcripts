"""
MP Aggregated Lookup Utility

Provides functionality to look up an MP's party affiliations across all terms
using the mps_aggregated_by_term.csv data.

Returns data in format: ["17.dönem Party Name", "18.dönem Party Name", ...]
"""

import os
import csv
from typing import List, Optional, Dict
import difflib

# Global lookup dictionary: {mp_name: {term: party}}
_mp_aggregated_data: Dict[str, Dict[int, str]] = {}
_all_mp_names: List[str] = []


def load_aggregated_lookup(csv_path: str = None) -> int:
    """
    Load the aggregated MP data from CSV.
    
    Args:
        csv_path: Path to mps_aggregated_by_term.csv (defaults to ../data/mps_aggregated_by_term.csv)
        
    Returns:
        Number of MPs loaded
    """
    global _mp_aggregated_data, _all_mp_names
    
    if csv_path is None:
        # Default path relative to this file
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "mps_aggregated_by_term.csv"
        )
    
    if not os.path.exists(csv_path):
        print(f"⚠️  MP aggregated lookup file not found: {csv_path}")
        return 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                mp_name = row['speech_giver'].strip()
                term_data = {}
                
                # Process each term column (term1, term2, ..., term27, term28)
                for term_num in range(1, 29):  # Terms 1-28
                    term_col = f'term{term_num}'
                    if term_col in row:
                        party = row[term_col].strip()
                        if party:  # Only store non-empty values
                            term_data[term_num] = party
                
                if term_data:  # Only store MPs with at least one term
                    _mp_aggregated_data[mp_name] = term_data
                    _all_mp_names.append(mp_name)
        
        print(f"✅ Loaded {len(_mp_aggregated_data)} MPs from {os.path.basename(csv_path)}")
        return len(_mp_aggregated_data)
        
    except Exception as e:
        print(f"❌ Error loading MP aggregated lookup: {e}")
        return 0


def get_mp_party_list(mp_name: str, fuzzy_match: bool = True, threshold: float = 0.85) -> List[str]:
    """
    Get the party affiliations for an MP across all terms.
    
    Args:
        mp_name: Name of the MP
        fuzzy_match: If True, try fuzzy matching if exact match fails
        threshold: Similarity threshold for fuzzy matching (0.0-1.0)
        
    Returns:
        List of strings in format ["17.dönem Party Name", "18.dönem Party Name", ...]
        Empty list if MP not found
    """
    if not mp_name:
        return []
    
    mp_name = mp_name.strip()
    
    # 1. Exact match
    if mp_name in _mp_aggregated_data:
        term_data = _mp_aggregated_data[mp_name]
        return format_party_list(term_data)
    
    # 2. Fuzzy match (if enabled)
    if fuzzy_match and _all_mp_names:
        matches = difflib.get_close_matches(
            mp_name, 
            _all_mp_names, 
            n=1, 
            cutoff=threshold
        )
        
        if matches:
            matched_name = matches[0]
            term_data = _mp_aggregated_data[matched_name]
            # print(f"   🔍 Fuzzy match: '{mp_name}' -> '{matched_name}'")
            return format_party_list(term_data)
    
    return []


def format_party_list(term_data: Dict[int, str]) -> List[str]:
    """
    Format term data into list of strings.
    
    Args:
        term_data: Dictionary of {term_num: party_name}
        
    Returns:
        List of strings like ["17.dönem Party Name", "18.dönem Party Name"]
    """
    result = []
    for term_num in sorted(term_data.keys()):
        party = term_data[term_num]
        result.append(f"{term_num}.dönem {party}")
    return result


def get_terms_served(mp_name: str, fuzzy_match: bool = True, threshold: float = 0.85) -> List[int]:
    """
    Get list of term numbers an MP served.
    
    Args:
        mp_name: Name of the MP
        fuzzy_match: If True, try fuzzy matching if exact match fails
        threshold: Similarity threshold for fuzzy matching (0.0-1.0)
        
    Returns:
        List of term numbers (e.g., [17, 18, 19])
    """
    if not mp_name:
        return []
    
    mp_name = mp_name.strip()
    
    # Exact match
    if mp_name in _mp_aggregated_data:
        return sorted(_mp_aggregated_data[mp_name].keys())
    
    # Fuzzy match
    if fuzzy_match and _all_mp_names:
        matches = difflib.get_close_matches(
            mp_name, 
            _all_mp_names, 
            n=1, 
            cutoff=threshold
        )
        
        if matches:
            matched_name = matches[0]
            return sorted(_mp_aggregated_data[matched_name].keys())
    
    return []


# Auto-load on import
_loaded_count = load_aggregated_lookup()

if __name__ == "__main__":
    # Test the module
    print("\n" + "=" * 80)
    print("TESTING MP AGGREGATED LOOKUP")
    print("=" * 80)
    
    # Test cases
    test_cases = [
        "Abdullah Azmi Torun",
        "Turgut Özal",
        "Özgür Özel",
        "A. Orhan Öztrak",
        "NonExistent MP",
    ]
    
    for mp_name in test_cases:
        party_list = get_mp_party_list(mp_name)
        terms_served = get_terms_served(mp_name)
        
        status = "✅" if party_list else "❌"
        print(f"\n{status} {mp_name}:")
        if party_list:
            print(f"   Party List: {party_list}")
            print(f"   Terms: {terms_served}")
        else:
            print(f"   Not found")
    
    # Test fuzzy matching
    print("\n" + "=" * 80)
    print("TESTING FUZZY MATCHING")
    print("=" * 80)
    
    fuzzy_test = "Turğut Ozal"  # Typo
    party_list = get_mp_party_list(fuzzy_test, fuzzy_match=True)
    print(f"Query: '{fuzzy_test}'")
    print(f"Result: {party_list}")
