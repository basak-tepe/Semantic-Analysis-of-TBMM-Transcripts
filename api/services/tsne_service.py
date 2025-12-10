"""Service for t-SNE coordinate data operations."""
import csv
from pathlib import Path
from typing import Dict, List, Optional

from api.config import WIDID_RESULTS_DIR


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
                    data_points.append({
                        'target_word': row['target_word'],
                        'term': int(row['term']),
                        'year': int(row['year']),
                        'tsne_x': float(row['tsne_x']),
                        'tsne_y': float(row['tsne_y']),
                        'cluster_id': int(row['cluster_id']),
                        'context': row['context']
                    })
        except Exception as e:
            print(f"Error reading CSV file {csv_path}: {e}")
            return []
        
        return data_points


# Global instance
tsne_service = TSNEService()

