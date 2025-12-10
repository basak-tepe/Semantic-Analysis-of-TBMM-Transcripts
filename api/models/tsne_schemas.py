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
