"""
Pydantic schemas for Annual Review API responses.
"""
from typing import List
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
    hours: float
    description: str
    color: str


class ShortestSpeakerResponse(BaseModel):
    """Response for the shortest speaker (by average speech length)."""
    name: str
    avgMinutes: float
    speeches: int
    description: str
    color: str


class LongestSpeakerResponse(BaseModel):
    """Response for the longest speaker (by average speech length)."""
    name: str
    avgMinutes: float
    speeches: int
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
    mostTalkedTopic: MostTalkedTopicResponse
    mostActiveMp: MostActiveMpResponse
    shortestSpeaker: ShortestSpeakerResponse
    longestSpeaker: LongestSpeakerResponse
    nicheTopic: NicheTopicResponse
    decliningInterest: DecliningInterestResponse
    mostDiverseDebate: MostDiverseDebateResponse


class YearInfo(BaseModel):
    """Information about an available year."""
    term: int
    year: int


class AvailableYearsResponse(BaseModel):
    """Response for available years."""
    years: List[YearInfo]

