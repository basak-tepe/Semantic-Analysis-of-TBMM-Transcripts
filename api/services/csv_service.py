"""Service for loading and parsing CSV data."""
import ast
import csv
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from api.config import MP_LOOKUP_CSV, TOPIC_SUMMARY_CSV


class CSVService:
    """Service for handling CSV data operations."""
    
    def __init__(self):
        self._mp_lookup: Optional[Dict] = None
        self._topic_summary: Optional[pd.DataFrame] = None
        self._mp_id_map: Optional[Dict[str, str]] = None
    
    def _generate_mp_id(self, name: str) -> str:
        """Generate a unique ID for an MP based on their name."""
        return hashlib.md5(name.encode('utf-8')).hexdigest()[:8]
    
    def load_mp_lookup(self) -> Dict:
        """Load MP lookup data from CSV."""
        if self._mp_lookup is not None:
            return self._mp_lookup
        
        if not MP_LOOKUP_CSV.exists():
            return {}
        
        mp_lookup = {}
        mp_id_map = {}
        
        with open(MP_LOOKUP_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['speech_giver'].strip()
                if not name:
                    continue
                
                party = row['political_party'].strip() if row.get('political_party') else None
                
                # Parse terms - handle both string representation and empty
                terms_str = row.get('terms', '[]').strip()
                if terms_str and terms_str != '[]':
                    try:
                        terms = ast.literal_eval(terms_str)
                        if not isinstance(terms, list):
                            terms = []
                    except (ValueError, SyntaxError):
                        terms = []
                else:
                    terms = []
                
                mp_id = self._generate_mp_id(name)
                mp_lookup[mp_id] = {
                    'name': name,
                    'party': party or 'Unknown',
                    'terms': terms
                }
                mp_id_map[name] = mp_id
        
        self._mp_lookup = mp_lookup
        self._mp_id_map = mp_id_map
        return mp_lookup
    
    def load_topic_summary(self) -> pd.DataFrame:
        """Load topic summary data from CSV."""
        if self._topic_summary is not None:
            return self._topic_summary
        
        if not TOPIC_SUMMARY_CSV.exists():
            return pd.DataFrame()
        
        # Read CSV in chunks to handle large files
        try:
            df = pd.read_csv(TOPIC_SUMMARY_CSV, low_memory=False)
            self._topic_summary = df
            return df
        except Exception as e:
            print(f"Error loading topic_summary.csv: {e}")
            return pd.DataFrame()
    
    def get_mp_by_id(self, mp_id: str) -> Optional[Dict]:
        """Get MP data by ID."""
        lookup = self.load_mp_lookup()
        return lookup.get(mp_id)
    
    def get_mp_id_by_name(self, name: str) -> Optional[str]:
        """Get MP ID by name."""
        if self._mp_id_map is None:
            self.load_mp_lookup()
        return self._mp_id_map.get(name) if self._mp_id_map else None
    
    def get_all_mp_ids(self) -> List[str]:
        """Get all MP IDs."""
        lookup = self.load_mp_lookup()
        return list(lookup.keys())
    
    def get_topics_for_mp(self, mp_name: str, top_n: int = 4) -> List[Dict]:
        """Get top topics for an MP."""
        df = self.load_topic_summary()
        
        if df.empty:
            return []
        
        # Filter by speech_giver
        if 'speech_giver' not in df.columns:
            return []
        
        mp_topics = df[df['speech_giver'] == mp_name].copy()
        
        if mp_topics.empty:
            return []
        
        # Calculate total speeches for percentage
        total_speeches = mp_topics['count'].sum()
        
        # Get top N topics by count
        top_topics = mp_topics.nlargest(top_n, 'count')
        
        results = []
        for _, row in top_topics.iterrows():
            topic_name = row.get('Name', 'Unknown Topic')
            if pd.isna(topic_name):
                topic_name = 'Unknown Topic'
            
            count = int(row.get('count', 0))
            percentage = round((count / total_speeches * 100), 1) if total_speeches > 0 else 0.0
            
            results.append({
                'name': str(topic_name),
                'count': count,
                'percentage': percentage
            })
        
        return results
    
    def format_terms(self, terms: List[int]) -> List[str]:
        """Format term numbers into readable format like '2015-2019'."""
        # Map term numbers to approximate years
        # Term 17: 1983-1987, Term 18: 1987-1991, etc.
        # This is approximate - adjust based on actual term dates
        term_year_map = {
            17: (1983, 1987), 18: (1987, 1991), 19: (1991, 1995),
            20: (1995, 1999), 21: (1999, 2002), 22: (2002, 2007),
            23: (2007, 2011), 24: (2011, 2015), 25: (2015, 2018),
            26: (2018, 2023), 27: (2023, 2028), 28: (2023, 2028)
        }
        
        formatted_terms = []
        for term in sorted(terms):
            if term in term_year_map:
                start, end = term_year_map[term]
                formatted_terms.append(f"{start}-{end}")
            else:
                formatted_terms.append(f"Term {term}")
        
        return formatted_terms


# Global instance
csv_service = CSVService()

