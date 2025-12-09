"""Service for t-SNE image operations."""
import base64
import re
from pathlib import Path
from typing import Dict, List, Optional

from api.config import ASSETS_DIR


class TSNEService:
    """Service for t-SNE image operations."""
    
    def __init__(self):
        self._available_words: Optional[List[str]] = None
    
    def get_available_words(self) -> List[str]:
        """Get list of available words from assets folder."""
        if self._available_words is not None:
            return self._available_words
        
        words = []
        if not ASSETS_DIR.exists():
            return words
        
        # Look for folders matching pattern: {word}-tsne-widid
        for folder in ASSETS_DIR.iterdir():
            if folder.is_dir() and folder.name.endswith('-tsne-widid'):
                word = folder.name.replace('-tsne-widid', '')
                words.append(word)
        
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


# Global instance
tsne_service = TSNEService()

