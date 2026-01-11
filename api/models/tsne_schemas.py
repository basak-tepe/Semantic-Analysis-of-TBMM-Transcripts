"""Pydantic models for t-SNE endpoints."""
from typing import List, Optional
from pydantic import BaseModel


class WordsResponse(BaseModel):
    """Response for available words."""
    words: List[str]


class TSNEDataPoint(BaseModel):
    """t-SNE data point from CSV with coordinates and context."""
    target_word: str
    term: int
    year: int
    calendar_year: Optional[int] = None  # Extracted from session_date (e.g., 2018)
    calendar_year_range: str  # Format: "2018" (single year from session_date)
    display_label: str  # Format: "2018 (d26y3)" (calendar year with term-year info)
    tsne_x: float
    tsne_y: float
    cluster_id: int
    context: str
    session_date: Optional[str] = None
    file: Optional[str] = None


class TSNEDataResponse(BaseModel):
    """Response for t-SNE coordinate data points."""
    word: str
    data: List[TSNEDataPoint]
