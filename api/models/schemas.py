"""Pydantic models for API request/response schemas."""
from typing import List, Optional
from pydantic import BaseModel


class MPListItem(BaseModel):
    """MP list item with basic information."""
    id: str
    name: str
    party: str


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
    party: str
    terms: List[str]
    topics: List[Topic]
    activity: List[ActivityYear]
    stance: str


class MPListResponse(BaseModel):
    """Response for list of MPs."""
    mps: List[MPListItem]


class MPDetailResponse(BaseModel):
    """Response for MP details."""
    id: str
    data: MPDetail

