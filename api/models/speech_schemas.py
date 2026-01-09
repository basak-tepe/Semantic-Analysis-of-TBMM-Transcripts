"""Pydantic schemas for speech search API."""
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class NEREntity(BaseModel):
    """Named Entity Recognition entity."""
    entity: str = Field(..., description="Entity name")
    entity_group: str = Field(..., description="Entity type: PER (Person), LOC (Location), ORG (Organization)")
    frequency: int = Field(..., description="Number of times entity appears in the speech")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    wikipedia_url: Optional[str] = Field(None, description="Wikipedia URL if linked")


class SpeechDocument(BaseModel):
    """Individual speech document from Elasticsearch."""
    id: str
    session_id: Optional[str] = None
    term: Optional[int] = None
    year: Optional[int] = None
    file: Optional[str] = None
    speech_no: Optional[int] = None
    province: Optional[str] = None
    speech_giver: Optional[str] = None
    political_party: Optional[str] = None
    terms_served: Optional[str] = None
    speech_title: Optional[str] = None
    page_ref: Optional[str] = None
    content: Optional[str] = None
    session_date: Optional[str] = None
    hdbscan_topic_id: Optional[int] = None
    hdbscan_topic_label: Optional[str] = None
    keywords: Optional[List[str]] = None
    keywords_str: Optional[str] = None
    ner_entities: Optional[List[NEREntity]] = None


class SpeechSearchResponse(BaseModel):
    """Response for speech search endpoint."""
    total: int = Field(..., description="Total number of matching speeches")
    page: int = Field(..., description="Current page number (1-based)")
    size: int = Field(..., description="Number of results per page")
    total_pages: int = Field(..., description="Total number of pages")
    speeches: List[SpeechDocument] = Field(..., description="List of speech documents")


class SpeechFacets(BaseModel):
    """Facet counts for filtering."""
    terms: List[dict] = Field(default_factory=list, description="Available terms with counts")
    years: List[dict] = Field(default_factory=list, description="Available years with counts")
    parties: List[dict] = Field(default_factory=list, description="Political parties with counts")
    provinces: List[dict] = Field(default_factory=list, description="Provinces with counts")
    topics: List[dict] = Field(default_factory=list, description="Topics with counts")


class SpeechStats(BaseModel):
    """Index statistics."""
    total_speeches: int = Field(..., description="Total number of speeches in index")
    total_sessions: int = Field(..., description="Total number of unique sessions processed")
    total_mps: int = Field(..., description="Total number of unique MPs")
    total_mps_from_term_17: int = Field(..., description="Total number of MPs who served starting from term 17 or later")
    total_topics: int = Field(..., description="Total number of unique topics")
    terms_range: dict = Field(default_factory=dict, description="Min/max term numbers")
    years_range: dict = Field(default_factory=dict, description="Min/max years")
