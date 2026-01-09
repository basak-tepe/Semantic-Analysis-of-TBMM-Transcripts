"""Configuration settings for the API."""
import os
from pathlib import Path
from typing import Tuple

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Elasticsearch configuration
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")

# Data directory
DATA_DIR = PROJECT_ROOT / "data"

# CSV file paths
MPS_AGGREGATED_CSV = DATA_DIR / "mps_aggregated_by_term.csv"
TOPIC_SUMMARY_CSV = DATA_DIR / "topic_summary.csv"

# Deprecated (kept for reference)
# MP_LOOKUP_CSV = DATA_DIR / "mp_lookup.csv"  # Replaced by mps_aggregated_by_term.csv

# Widid results directory for t-SNE coordinate CSV data
WIDID_RESULTS_DIR = PROJECT_ROOT / "src" / "widid_results"

# CORS settings
# Allow custom origins via environment variable, or use defaults
CORS_ORIGINS = os.getenv("CORS_ORIGINS","https://tbmm-frontend-zo6hhrtq7a-ey.a.run.app,http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001").split(",")

# For production, you can set CORS_ORIGINS="*" to allow all origins (less secure but convenient)
# Or set specific domains: CORS_ORIGINS="https://yourfrontend.com,https://www.yourfrontend.com"

# Term to calendar year range mapping
TERM_YEAR_MAP = {
    17: (1983, 1987), 18: (1987, 1991), 19: (1991, 1995),
    20: (1995, 1999), 21: (1999, 2002), 22: (2002, 2007),
    23: (2007, 2011), 24: (2011, 2015), 25: (2015, 2015),
    26: (2015, 2018), 27: (2018, 2023), 28: (2023, 2028)
}


def get_calendar_year_range(term: int, year_in_term: int) -> Tuple[int, int]:
    """
    Convert term and year-in-term to actual calendar year range.
    
    Args:
        term: Term number (17-28)
        year_in_term: Year within the term (1-5)
    
    Returns:
        Tuple of (start_year, end_year) for that period
        
    Example:
        get_calendar_year_range(17, 1) -> (1983, 1984)
        get_calendar_year_range(21, 2) -> (2000, 2001)
    """
    if term not in TERM_YEAR_MAP:
        return (0, 0)
    
    term_start, term_end = TERM_YEAR_MAP[term]
    calendar_year = term_start + (year_in_term - 1)
    
    # Don't exceed term end year
    if calendar_year >= term_end:
        calendar_year = term_end - 1
    
    return (calendar_year, calendar_year + 1)


def get_term_year_display(term: int, year_in_term: int) -> str:
    """
    Get display string for term/year combination.
    
    Example:
        get_term_year_display(17, 1) -> "d17y1 (1983-1984)"
        get_term_year_display(21, 2) -> "d21y2 (2000-2001)"
    """
    start, end = get_calendar_year_range(term, year_in_term)
    if start == 0:
        return f"d{term}y{year_in_term}"
    return f"d{term}y{year_in_term} ({start}-{end})"


def get_term_year_sort_key(term: int, year_in_term: int) -> int:
    """
    Get sort key for proper ordering by term first, then year.
    
    Returns:
        Integer key where higher = later in time
        
    Example:
        d17y1 -> 1701
        d17y5 -> 1705
        d18y1 -> 1801
    """
    return term * 100 + year_in_term

