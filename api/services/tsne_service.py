"""Service for t-SNE coordinate data operations."""
import csv
from pathlib import Path
from typing import Dict, List, Optional

from api.config import WIDID_RESULTS_DIR


def extract_calendar_year(session_date: str) -> Optional[int]:
    """Extract calendar year from session_date string (DD.MM.YYYY format)."""
    if not session_date:
        return None
    try:
        parts = session_date.split('.')
        if len(parts) >= 3:
            return int(parts[2])  # Year is the third part
    except (ValueError, IndexError):
        pass
    return None


class TSNEService:
    """Service for t-SNE coordinate data operations."""
    
    def __init__(self):
        self._available_words: Optional[List[str]] = None
    
    def get_available_words(self) -> List[str]:
        """Get list of available words from widid_results folder."""
        if self._available_words is not None:
            return self._available_words
        
        words = []
        if not WIDID_RESULTS_DIR.exists():
            return words
        
        # Look for folders containing tsne_{word}.csv files
        for folder in WIDID_RESULTS_DIR.iterdir():
            if folder.is_dir():
                csv_file = folder / f"tsne_{folder.name}.csv"
                if csv_file.exists():
                    words.append(folder.name)
        
        self._available_words = sorted(words)
        return words
    
    def get_tsne_data_for_word(self, word: str) -> List[Dict]:
        """Get all t-SNE coordinate data points for a specific word from CSV."""
        csv_path = WIDID_RESULTS_DIR / word / f"tsne_{word}.csv"
        
        if not csv_path.exists():
            return []
        
        data_points = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    term = int(row['term'])
                    year = int(row['year'])
                    session_date = row.get('session_date', '')
                    
                    # Extract calendar year from session_date
                    calendar_year = extract_calendar_year(session_date)
                    
                    # Set calendar_year_range and display_label based on extracted year
                    if calendar_year:
                        calendar_year_range = str(calendar_year)
                        display_label = f"{calendar_year} (d{term}y{year})"
                    else:
                        # Fallback if session_date is missing or malformed
                        calendar_year_range = ""
                        display_label = f"d{term}y{year}"
                    
                    data_points.append({
                        'target_word': row['target_word'],
                        'term': term,
                        'year': year,
                        'calendar_year': calendar_year,
                        'calendar_year_range': calendar_year_range,
                        'display_label': display_label,
                        'tsne_x': float(row['tsne_x']),
                        'tsne_y': float(row['tsne_y']),
                        'cluster_id': int(row['cluster_id']),
                        'context': row['context'],
                        'session_date': session_date if session_date else None,
                        'file': row.get('file')
                    })
        except Exception as e:
            print(f"Error reading CSV file {csv_path}: {e}")
            return []
        
        return data_points


# Global instance
tsne_service = TSNEService()

