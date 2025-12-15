"""
MP Name Normalization Module

This module provides utilities for normalizing MP names to prevent duplicates
caused by extraction inconsistencies (e.g., apostrophes, spelling variations).

Usage:
    from mp_name_normalizer import normalize_mp_name, find_similar_names
    
    normalized = normalize_mp_name("John Doe'nın")  # Returns "John Doe"
"""

import re
import difflib
from typing import List, Dict, Tuple, Optional


def normalize_mp_name(name: str) -> str:
    """
    Normalize MP name by removing apostrophes, commas, and cleaning whitespace.
    
    Takes the part before separators to handle cases like:
    - "John Doe" and "John Doe'" -> both become "John Doe"
    - "Ahmet Yılmaz'ın" -> becomes "Ahmet Yılmaz"
    - "Mehmet Ali, additional text" -> becomes "Mehmet Ali"
    
    Args:
        name: Raw MP name from extraction
        
    Returns:
        Normalized name without apostrophe/comma suffix
    """
    if not name:
        return ""
    
    # Split by apostrophe and take the first part
    # Handles multiple apostrophe types:
    # ' = U+0027 (APOSTROPHE)
    # ' = U+2019 (RIGHT SINGLE QUOTATION MARK) 
    # ‛ = U+201B (SINGLE HIGH-REVERSED-9 QUOTATION MARK)
    # ` = U+0060 (GRAVE ACCENT)
    name = re.split(r"['\u2019'\u201B`]", name)[0]
    
    # Also split by comma and semicolon and take the first part
    # This handles cases where additional text is appended after these separators
    name = re.split(r"[,;]", name)[0]
    
    # Normalize whitespace
    name = re.sub(r"\s+", " ", name).strip()
    
    return name


def is_valid_name_length(name: str, max_length: int = 45) -> bool:
    """
    Check if name is within acceptable length.
    
    Names longer than max_length typically indicate extraction errors
    where additional text was incorrectly included in the name field.
    
    Args:
        name: Name to check
        max_length: Maximum acceptable length (default: 45 characters)
        
    Returns:
        True if name length is valid, False otherwise
    """
    return len(name) <= max_length


def contains_conjunction_words(name: str) -> bool:
    """
    Check if name contains Turkish conjunction words as separate tokens.
    
    Names containing "ve" (and) or "ile" (with) as standalone words typically
    indicate compound names or concatenated text from multiple MPs.
    
    Examples of problematic names:
    - "Ahmet Yılmaz ve Mehmet Ali" (two people)
    - "Name ile Province Milletvekili" (name with description)
    
    Args:
        name: Name to check
        
    Returns:
        True if name contains "ve" or "ile" as separate words, False otherwise
    """
    if not name:
        return False
    
    # Split by whitespace to get individual words
    words = name.split()
    
    # Check if "ve" or "ile" exists as a standalone word (case-insensitive)
    # Handle Turkish-specific case conversion: İ → i, I → ı
    for word in words:
        # Replace Turkish-specific characters before lowercasing
        # İ (Turkish capital I with dot) → i
        # I (Latin capital I) → keep as I for now, will lowercase to i
        word_lower = word.replace('İ', 'i').lower()
        # After lowercasing, also check the version where I→i (for Latin I)
        word_latin_lower = word.replace('I', 'i').lower()
        
        if word_lower in ['ve', 'ile'] or word_latin_lower in ['ve', 'ile']:
            return True
    
    return False


def is_valid_mp_name(name: str, max_length: int = 45) -> bool:
    """
    Check if name passes all validation criteria.
    
    A valid MP name should:
    1. Be within the maximum length (default: 45 characters)
    2. NOT contain conjunction words "ve" or "ile" as separate tokens
    
    Args:
        name: Name to check
        max_length: Maximum acceptable length (default: 45 characters)
        
    Returns:
        True if name is valid, False if it's problematic
    """
    # Check length
    if not is_valid_name_length(name, max_length):
        return False
    
    # Check for conjunction words
    if contains_conjunction_words(name):
        return False
    
    return True


def get_first_n_words(name: str, n: int = 3) -> str:
    """
    Extract first N words from name for fuzzy matching.
    
    Args:
        name: Full name string
        n: Number of words to extract (default: 3)
        
    Returns:
        String containing first N words
        
    Example:
        >>> get_first_n_words("Ahmet Mehmet Yılmaz Öztürk", 3)
        "Ahmet Mehmet Yılmaz"
    """
    words = name.split()
    return " ".join(words[:n])


def calculate_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity ratio between two names.
    
    Uses difflib.SequenceMatcher to compute similarity ratio.
    
    Args:
        name1: First name
        name2: Second name
        
    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    return difflib.SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


def find_similar_names(
    name: str, 
    existing_names: List[str], 
    threshold: float = 0.9,
    compare_first_n_words: int = 3,
    lookup_data: Optional[Dict[str, Dict]] = None
) -> List[str]:
    """
    Find names with similar first N words using fuzzy matching.
    
    This helps identify duplicates like:
    - "John Kernel Smith" and "John Kernell Smith" (spelling variation)
    - "Ahmet Yılmaz" and "Ahmet Yilmaz" (accent variation)
    
    Names without party data are considered as last resort matches.
    
    Args:
        name: Name to find matches for
        existing_names: List of existing names to search in
        threshold: Similarity threshold (0.0-1.0), default 0.9 for ~90% match
        compare_first_n_words: Number of words to compare (default: 3)
        lookup_data: Optional dict mapping names to their data (party, terms)
                     Used to prioritize names with party data
        
    Returns:
        List of matching names, sorted by:
        1. Similarity (highest first)
        2. Has party data (preferred over no party data)
        
    Example:
        >>> find_similar_names("John Kernel", ["John Kernell", "Jane Doe"], 0.9)
        ["John Kernell"]
    """
    if not name or not existing_names:
        return []
    
    # Get first N words of the target name
    name_prefix = get_first_n_words(name, compare_first_n_words)
    
    matches = []
    for existing_name in existing_names:
        # Skip exact match (same name)
        if existing_name == name:
            continue
            
        # Get first N words of existing name
        existing_prefix = get_first_n_words(existing_name, compare_first_n_words)
        
        # Calculate similarity
        similarity = calculate_similarity(name_prefix, existing_prefix)
        
        if similarity >= threshold:
            # Check if this name has party data (higher priority)
            has_party_data = False
            if lookup_data and existing_name in lookup_data:
                party = lookup_data[existing_name].get('party')
                has_party_data = bool(party and party.strip())
            
            matches.append((existing_name, similarity, has_party_data))
    
    # Sort by similarity first, then by has_party_data (True before False)
    # This means: high similarity + has party data comes first
    # But names without party data can still match as last resort
    matches.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    # Return just the names, not the similarity scores or party flags
    return [match[0] for match in matches]


def select_canonical_name(
    name_variants: List[str], 
    lookup_data: Dict[str, Dict]
) -> str:
    """
    Select the best canonical name from variants.
    
    Selection criteria (in priority order):
    1. Most complete party data (not None/empty)
    2. Most complete terms data (longest list)
    3. Shortest name (as tiebreaker)
    
    Args:
        name_variants: List of name variants to choose from
        lookup_data: Dictionary mapping names to their data (party, terms)
        
    Returns:
        The canonical name from the variants
        
    Example:
        >>> variants = ["John Doe", "John Doe'"]
        >>> data = {
        ...     "John Doe": {"party": "Party A", "terms": [17, 18]},
        ...     "John Doe'": {"party": None, "terms": []}
        ... }
        >>> select_canonical_name(variants, data)
        "John Doe"
    """
    if not name_variants:
        return ""
    
    if len(name_variants) == 1:
        return name_variants[0]
    
    # Score each variant
    scored_variants = []
    for name in name_variants:
        data = lookup_data.get(name, {"party": None, "terms": []})
        
        # Calculate completeness score
        party_score = 1 if data.get("party") else 0
        terms_score = len(data.get("terms", []))
        length_score = -len(name)  # Negative so shorter is better
        
        # Weighted score: party and terms are more important than length
        total_score = (party_score * 100) + (terms_score * 10) + length_score
        
        scored_variants.append((name, total_score, party_score, terms_score))
    
    # Sort by total score (highest first)
    scored_variants.sort(key=lambda x: x[1], reverse=True)
    
    return scored_variants[0][0]


def merge_mp_data(
    canonical_name: str,
    variant_names: List[str],
    lookup_data: Dict[str, Dict]
) -> Dict:
    """
    Merge data from multiple name variants into canonical entry.
    
    Combines party and terms information from all variants,
    preferring non-empty values.
    
    Args:
        canonical_name: The canonical name to merge data into
        variant_names: List of variant names to merge from
        lookup_data: Dictionary mapping names to their data
        
    Returns:
        Merged data dictionary with 'party' and 'terms' keys
    """
    # Start with canonical name's data
    merged = lookup_data.get(canonical_name, {"party": None, "terms": []}).copy()
    
    # Collect all parties and terms from variants
    all_parties = []
    all_terms = set()
    
    for name in [canonical_name] + variant_names:
        if name not in lookup_data:
            continue
            
        data = lookup_data[name]
        party = data.get("party")
        terms = data.get("terms", [])
        
        if party:
            all_parties.append(party)
        
        if terms:
            all_terms.update(terms)
    
    # Use the first non-empty party found
    if all_parties:
        merged["party"] = all_parties[0]
    
    # Merge all unique terms and sort
    if all_terms:
        merged["terms"] = sorted(list(all_terms))
    
    return merged


def group_similar_names(
    names: List[str],
    lookup_data: Dict[str, Dict],
    threshold: float = 0.9
) -> Dict[str, List[str]]:
    """
    Group similar names together for deduplication.
    
    Returns a mapping of canonical names to their variants.
    
    Args:
        names: List of all names to group
        lookup_data: Dictionary mapping names to their data
        threshold: Similarity threshold for grouping
        
    Returns:
        Dictionary mapping canonical_name -> [variant1, variant2, ...]
    """
    groups = {}
    processed = set()
    
    for name in names:
        if name in processed:
            continue
        
        # Find all similar names, passing lookup_data to prioritize names with party data
        similar = find_similar_names(name, names, threshold, lookup_data=lookup_data)
        
        if not similar:
            # No matches, this name is canonical
            groups[name] = []
            processed.add(name)
        else:
            # Found matches - determine canonical name
            all_variants = [name] + similar
            canonical = select_canonical_name(all_variants, lookup_data)
            
            # Add to group
            variants = [v for v in all_variants if v != canonical]
            groups[canonical] = variants
            
            # Mark all as processed
            processed.update(all_variants)
    
    return groups
