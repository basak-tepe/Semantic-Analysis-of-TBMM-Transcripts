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

# Excluded topic IDs for analysis endpoints
# These topics are excluded from MP analysis and annual review but remain available in speech search
EXCLUDED_TOPIC_IDS = [251, 253]  # Topic 251: "Meclis, şehit, PKK, demokrasi, terör" | Topic 253: "Meclis, PKK, AKP, şehit, demokrasi"

# CORS settings
# Allow custom origins via environment variable, or use defaults
CORS_ORIGINS = os.getenv("CORS_ORIGINS","https://tbmm-frontend-zo6hhrtq7a-ey.a.run.app,http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001").split(",")

# For production, you can set CORS_ORIGINS="*" to allow all origins (less secure but convenient)
# Or set specific domains: CORS_ORIGINS="https://yourfrontend.com,https://www.yourfrontend.com"

# Exact term-year to calendar year range mapping
TERM_YEAR_EXACT_MAP = {
    17 : {1:[1983,1984], 2:[1984,1985], 3:[1985,1986], 4:[1986,1987], 5:[1987,1987]},
    18 : {1:[1987,1988], 2:[1988,1989], 3:[1989,1990], 4:[1990,1991], 5:[1991,1991]},
    19 : {1:[1991,1992], 2:[1992,1993], 3:[1993,1994], 4:[1994,1995], 5:[1995,1995]},
    20 : {1:[1996,1996], 2:[1996,1997], 3:[1997,1998], 4:[1998,1999]},
    21 : {1:[1999,1999], 2:[1999,2000], 3:[2000,2001], 4:[2001,2002], 5:[2002,2002]},
    22 : {1:[2002,2003], 2:[2003,2004], 3:[2004,2005], 4:[2005,2006], 5:[2006,2007]},       
    23 : {1:[2007,2007], 2:[2007,2008], 3:[2008,2009], 4:[2009,2010], 5:[2010,2011]},
    24 : {1:[2011,2011], 2:[2011,2012], 3:[2012,2013], 4:[2013,2014], 5:[2014,2015]},
    25 : {1:[2015,2015], 2:[2015,2015]},
    26 : {1:[2015,2016], 2:[2016,2017], 3:[2017,2018]}, 
    27 : {1:[2018,2018], 2:[2018,2019], 3:[2019,2020], 4:[2020,2021], 5:[2021,2022], 6:[2022,2023]},
    28 : {1:[2023,2024]}
}

# Term to calendar year range mapping (derived from exact map for backward compatibility)
# This generates the overall term range from the exact map
TERM_YEAR_MAP = {}
for term, years in TERM_YEAR_EXACT_MAP.items():
    if years:
        first_year = min(years.keys())
        last_year = max(years.keys())
        start = years[first_year][0]
        end = years[last_year][1]
        TERM_YEAR_MAP[term] = (start, end)


def get_calendar_year_range(term: int, year_in_term: int) -> Tuple[int, int]:
    """
    Convert term and year-in-term to actual calendar year range using exact mapping.
    
    Args:
        term: Term number (17-28)
        year_in_term: Year within the term (1-6, varies by term)
    
    Returns:
        Tuple of (start_year, end_year) for that period
        
    Example:
        get_calendar_year_range(17, 1) -> (1983, 1984)
        get_calendar_year_range(27, 6) -> (2022, 2023)
    """
    if term not in TERM_YEAR_EXACT_MAP:
        return (0, 0)
    
    term_years = TERM_YEAR_EXACT_MAP[term]
    if year_in_term not in term_years:
        return (0, 0)
    
    year_range = term_years[year_in_term]
    return (year_range[0], year_range[1])


def get_term_year_display(term: int, year_in_term: int) -> str:
    """
    Get display string for term/year combination.
    
    Example:
        get_term_year_display(17, 1) -> "d17y1 (1983-1984)"
        get_term_year_display(27, 6) -> "d27y6 (2022-2023)"
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

