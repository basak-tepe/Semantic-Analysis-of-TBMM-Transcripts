"""Pydantic models for t-SNE endpoints."""
from typing import List
from pydantic import BaseModel


class TSNEImage(BaseModel):
    """t-SNE image information."""
    term: int
    year: int
    png: str  # Base64 encoded PNG data URL


class WordsResponse(BaseModel):
    """Response for available words."""
    words: List[str]


class TSNEImagesResponse(BaseModel):
    """Response for t-SNE images."""
    word: str
    images: List[TSNEImage]
