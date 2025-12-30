"""Pydantic models for API request/response schemas."""
from typing import List, Optional, Dict
from pydantic import BaseModel


class MPListItem(BaseModel):
    """MP list item with basic information (lightweight for list view)."""
    id: str
    name: str
    # No party field - keep payload small for list view


class Topic(BaseModel):
    """Topic information."""
    name: str
    count: int
    percentage: float


class ActivityYear(BaseModel):
    """Activity data for a specific year."""
    year: str
    speeches: int
    laws: int
    votes: int


class MPDetail(BaseModel):
    """Complete MP profile information."""
    name: str
    party: List[str]  # List of strings like ["17.dönem Party1", "18.dönem Party2"]
    terms: List[str]
    topics: List[Topic]
    topics_by_party: Optional[Dict[str, List[Topic]]] = None  # Topics grouped by party name
    activity: List[ActivityYear]
    stance: str


class MPListResponse(BaseModel):
    """Response for list of MPs with pagination."""
    mps: List[MPListItem]
    total: int
    page: int
    limit: int
    total_pages: int


class MPDetailResponse(BaseModel):
    """Response for MP details."""
    id: str
    data: MPDetail

