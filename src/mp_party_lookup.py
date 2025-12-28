"""
MP Party Lookup Utility

Provides functionality to look up an MP's party affiliation for a specific term
using the mps_by_term.csv data.
"""

import os
import csv
from typing import Optional, Dict, Tuple
import difflib

# Global lookup dictionary: {(term, mp_name): party}
_party_lookup: Dict[Tuple[int, str], str] = {}
_mp_names_by_term: Dict[int, set] = {}  # For fuzzy matching within term


def load_party_lookup(csv_path: str = None) -> int:
    """
    Load the MP party lookup data from CSV.
    
    Args:
        csv_path: Path to mps_by_term.csv (defaults to ../data/mps_by_term.csv)
        
    Returns:
        Number of entries loaded
    """
    global _party_lookup, _mp_names_by_term
    
    if csv_path is None:
        # Default path relative to this file
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "mps_by_term.csv"
        )
    
    if not os.path.exists(csv_path):
        print(f"⚠️  MP party lookup file not found: {csv_path}")
        return 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                term = int(row['term'])
                mp_name = row['mp_name'].strip()
                party = row['party'].strip()
                
                # Store in lookup
                key = (term, mp_name)
                _party_lookup[key] = party
                
                # Track names per term for fuzzy matching
                if term not in _mp_names_by_term:
                    _mp_names_by_term[term] = set()
                _mp_names_by_term[term].add(mp_name)
        
        print(f"✅ Loaded {len(_party_lookup)} MP-term-party mappings from {os.path.basename(csv_path)}")
        return len(_party_lookup)
        
    except Exception as e:
        print(f"❌ Error loading MP party lookup: {e}")
        return 0


def get_party_for_term(mp_name: str, term: int, fuzzy_match: bool = True, threshold: float = 0.85) -> Optional[str]:
    """
    Get the party affiliation for an MP in a specific term.
    
    Args:
        mp_name: Name of the MP
        term: Term number (1-28)
        fuzzy_match: If True, try fuzzy matching if exact match fails
        threshold: Similarity threshold for fuzzy matching (0.0-1.0)
        
    Returns:
        Party name or None if not found
    """
    if not mp_name or term is None:
        return None
    
    mp_name = mp_name.strip()
    key = (term, mp_name)
    
    # 1. Exact match
    if key in _party_lookup:
        return _party_lookup[key]
    
    # 2. Fuzzy match (if enabled and term exists in our data)
    if fuzzy_match and term in _mp_names_by_term:
        matches = difflib.get_close_matches(
            mp_name, 
            _mp_names_by_term[term], 
            n=1, 
            cutoff=threshold
        )
        
        if matches:
            matched_name = matches[0]
            matched_key = (term, matched_name)
            party = _party_lookup.get(matched_key)
            
            if party:
                # print(f"   🔍 Fuzzy match: '{mp_name}' -> '{matched_name}' (term {term})")
                return party
    
    return None


def extract_term_from_id(doc_id: str) -> Optional[int]:
    """
    Extract term number from document ID.
    
    Args:
        doc_id: Document ID like "term27-year3-session21-48"
        
    Returns:
        Term number or None if not found
    """
    import re
    match = re.search(r'term(\d+)', doc_id)
    if match:
        return int(match.group(1))
    return None


# Auto-load on import
_loaded_count = load_party_lookup()

if __name__ == "__main__":
    # Test the module
    print("\n" + "=" * 80)
    print("TESTING MP PARTY LOOKUP")
    print("=" * 80)
    
    # Test cases
    test_cases = [
        ("Abdullah Azmi Torun", 1),
        ("Turgut Özal", 17),
        ("Özgür Özel", 27),
        ("NonExistent MP", 27),
    ]
    
    for mp_name, term in test_cases:
        party = get_party_for_term(mp_name, term)
        status = "✅" if party else "❌"
        print(f"{status} Term {term}, {mp_name}: {party or 'Not found'}")
    
    # Test ID extraction
    print("\n" + "=" * 80)
    print("TESTING ID EXTRACTION")
    print("=" * 80)
    
    test_ids = [
        "term27-year3-session21-48",
        "term17-year1-session01-5",
        "invalid-id",
    ]
    
    for doc_id in test_ids:
        term = extract_term_from_id(doc_id)
        print(f"ID: {doc_id} -> Term: {term}")
