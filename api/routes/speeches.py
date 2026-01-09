"""
Speech search API routes.
Provides endpoints for searching and browsing speeches via Elasticsearch.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import math

from api.models.speech_schemas import (
    SpeechDocument,
    SpeechSearchResponse,
    SpeechFacets,
    SpeechStats
)
from api.services.elasticsearch_service import es_service

router = APIRouter(prefix="/api/speeches", tags=["speeches"])


@router.get("/search", response_model=SpeechSearchResponse)
async def search_speeches(
    q: Optional[str] = Query(None, description="Full-text search query"),
    mp_name: Optional[str] = Query(None, alias="speaker", description="Filter by MP name"),
    term: Optional[int] = Query(None, description="Filter by parliamentary term (17-28)"),
    year: Optional[int] = Query(None, description="Filter by year within term (1-5)"),
    topic_id: Optional[int] = Query(None, description="Filter by topic ID"),
    topic_label: Optional[str] = Query(None, description="Filter by topic label"),
    province: Optional[str] = Query(None, description="Filter by province"),
    political_party: Optional[str] = Query(None, alias="party", description="Filter by political party"),
    from_date: Optional[str] = Query(None, description="Filter from date (format: dd.MM.yyyy)"),
    to_date: Optional[str] = Query(None, description="Filter to date (format: dd.MM.yyyy)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Results per page (max 100)"),
    sort_by: str = Query("date", description="Sort by: date, relevance")
):
    """
    Search for speeches with various filters and pagination.
    
    This endpoint proxies Elasticsearch queries, allowing the frontend to search
    and browse speeches without direct ES access.
    
    Examples:
    - Search for economy speeches: /api/speeches/search?q=ekonomi
    - Get MP's speeches: /api/speeches/search?mp_name=Recep%20Tayyip%20ERDOĞAN
    - Filter by term and year: /api/speeches/search?term=27&year=1
    - Paginate results: /api/speeches/search?page=2&size=50
    """
    try:
        # Calculate offset from page number
        from_ = (page - 1) * size
        
        # Execute search
        result = es_service.search_speeches(
            query_text=q,
            mp_name=mp_name,
            term=term,
            year=year,
            topic_id=topic_id,
            topic_label=topic_label,
            province=province,
            political_party=political_party,
            from_date=from_date,
            to_date=to_date,
            size=size,
            from_=from_,
            sort_by=sort_by
        )
        
        total = result.get('total', 0)
        speeches = result.get('speeches', [])
        
        # Calculate total pages
        total_pages = math.ceil(total / size) if size > 0 else 0
        
        return SpeechSearchResponse(
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
            speeches=[SpeechDocument(**s) for s in speeches]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching speeches: {str(e)}"
        )


@router.get("/facets", response_model=SpeechFacets)
async def get_facets():
    """
    Get available filter options with counts.
    
    Returns aggregated counts for:
    - Terms (parliamentary terms)
    - Years (year within term)
    - Political parties
    - Provinces
    - Topics
    
    Useful for building filter dropdowns in the frontend.
    """
    try:
        facets = es_service.get_facets()
        return SpeechFacets(**facets)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching facets: {str(e)}"
        )


@router.get("/filters")
async def get_filters():
    """
    Get filter options as flat arrays (frontend-friendly format).
    
    Returns:
    - parties: list of political party names
    - terms: list of parliamentary term numbers
    - years: list of year numbers (1-5)
    - speakers: list of MP names
    - topics: list of topic objects with id and label (e.g., [{"id": 42, "label": "Topic Label"}])
    """
    try:
        filters = es_service.get_filters()
        return filters
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching filters: {str(e)}"
        )


@router.get("/count")
async def get_count():
    """
    Get total number of speeches in the index.
    
    Returns:
    - count: total number of speeches
    """
    try:
        count = es_service.get_total_count()
        return {"count": count}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching count: {str(e)}"
        )


@router.get("/stats", response_model=SpeechStats)
async def get_stats():
    """
    Get overall index statistics.
    
    Returns:
    - Total number of speeches
    - Total number of unique MPs
    - Range of terms and years
    """
    try:
        stats = es_service.get_index_stats()
        return SpeechStats(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )


@router.get("/{speech_id}", response_model=SpeechDocument)
async def get_speech(speech_id: str):
    """
    Get a single speech by its ID.
    
    Args:
        speech_id: The Elasticsearch document ID
        
    Returns:
        Full speech document with all fields
    """
    try:
        speech = es_service.get_speech_by_id(speech_id)
        
        if speech is None:
            raise HTTPException(
                status_code=404,
                detail=f"Speech not found: {speech_id}"
            )
        
        return SpeechDocument(**speech)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching speech: {str(e)}"
        )


@router.get("/entities/search", response_model=SpeechSearchResponse)
async def search_by_entity(
    entity: str = Query(..., description="Entity name to search for"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type: PER, LOC, ORG"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Search speeches by NER entity name.
    
    Examples:
    - Find speeches mentioning "Ankara": /api/speeches/entities/search?entity=Ankara
    - Find speeches mentioning persons named "Ahmet": /api/speeches/entities/search?entity=Ahmet&entity_type=PER
    - Find speeches about organizations: /api/speeches/entities/search?entity=TBMM&entity_type=ORG
    """
    try:
        from_ = (page - 1) * size
        result = es_service.search_by_entity(
            entity_name=entity,
            entity_type=entity_type,
            size=size,
            from_=from_
        )
        
        total = result.get('total', 0)
        speeches = result.get('speeches', [])
        total_pages = math.ceil(total / size) if size > 0 else 0
        
        return SpeechSearchResponse(
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
            speeches=[SpeechDocument(**s) for s in speeches]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching by entity: {str(e)}"
        )


@router.get("/entities/top")
async def get_top_entities(
    entity_type: Optional[str] = Query(None, description="Filter by entity type: PER, LOC, ORG"),
    limit: int = Query(50, ge=1, le=200, description="Number of top entities to return")
):
    """
    Get top entities by frequency across all speeches.
    
    Returns the most frequently mentioned entities, optionally filtered by type.
    
    Examples:
    - Top 50 entities: /api/speeches/entities/top
    - Top 20 people: /api/speeches/entities/top?entity_type=PER&limit=20
    - Top locations: /api/speeches/entities/top?entity_type=LOC
    """
    try:
        entities = es_service.get_top_entities(entity_type=entity_type, limit=limit)
        return {
            "entities": entities,
            "total": len(entities),
            "entity_type": entity_type or "ALL"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching top entities: {str(e)}"
        )
