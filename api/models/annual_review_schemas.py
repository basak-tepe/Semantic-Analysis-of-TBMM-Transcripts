"""
Pydantic schemas for Annual Review API responses.
"""
from typing import List, Optional
from pydantic import BaseModel


class MostTalkedTopicResponse(BaseModel):
    """Response for the most talked about topic."""
    name: str
    mentions: int
    change: str
    description: str
    color: str


class MostActiveMpResponse(BaseModel):
    """Response for the most active MP."""
    name: str
    speeches: int
    province: str
    description: str
    color: str


class MostRepresentedProvinceResponse(BaseModel):
    """Response for the most represented province."""
    name: str
    speeches: int
    representatives: int
    description: str
    color: str


class NicheTopicResponse(BaseModel):
    """Response for the most niche topic."""
    name: str
    mp: str
    mentions: int
    description: str
    color: str


class DecliningInterestResponse(BaseModel):
    """Response for topic with declining interest."""
    name: str
    change: str
    previousYear: int
    currentYear: int
    description: str
    color: str


class MostDiverseDebateResponse(BaseModel):
    """Response for the most diverse debate."""
    name: str
    speakers: int
    perspectives: int
    description: str
    color: str


class AnnualReviewResponse(BaseModel):
    """Complete annual review response."""
    term: int
    year: int
    mostTalkedTopic: Optional[MostTalkedTopicResponse] = None
    mostActiveMp: Optional[MostActiveMpResponse] = None
    mostRepresentedProvince: Optional[MostRepresentedProvinceResponse] = None
    nicheTopic: Optional[NicheTopicResponse] = None
    decliningInterest: Optional[DecliningInterestResponse] = None
    mostDiverseDebate: Optional[MostDiverseDebateResponse] = None


class YearInfo(BaseModel):
    """Information about an available year."""
    term: int
    year: int


class AvailableYearsResponse(BaseModel):
    """Response for available years."""
    years: List[YearInfo]

