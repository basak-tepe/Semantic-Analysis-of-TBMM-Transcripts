"""Service for t-SNE image operations."""
import base64
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional

from api.config import ASSETS_DIR, WIDID_RESULTS_DIR


class TSNEService:
    """Service for t-SNE image operations."""
    
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
    
    def get_tsne_images_for_word(self, word: str) -> List[Dict]:
        """Get all t-SNE images for a specific word."""
        folder_path = ASSETS_DIR / f"{word}-tsne-widid"
        
        if not folder_path.exists():
            return []
        
        images = []
        pattern = re.compile(r'tsne_term(\d+)_year(\d+)_' + re.escape(word) + r'\.png')
        
        # Find all matching PNG files
        for png_file in folder_path.glob(f"tsne_term*_year*_{word}.png"):
            match = pattern.match(png_file.name)
            if match:
                term = int(match.group(1))
                year = int(match.group(2))
                
                # Read and encode image as base64
                try:
                    with open(png_file, 'rb') as f:
                        image_data = f.read()
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        images.append({
                            'term': term,
                            'year': year,
                            'png': f"data:image/png;base64,{base64_data}"
                        })
                except Exception as e:
                    print(f"Error reading {png_file}: {e}")
                    continue
        
        # Sort by term, then year
        images.sort(key=lambda x: (x['term'], x['year']))
        return images
    
    def get_tsne_data_for_word(self, word: str) -> List[Dict]:
        """Get all t-SNE data points for a specific word from CSV."""
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

