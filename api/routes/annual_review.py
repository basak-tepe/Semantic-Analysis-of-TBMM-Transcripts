"""
Annual Review API routes.
"""
from fastapi import APIRouter, HTTPException
from api.models.annual_review_schemas import (
    AnnualReviewResponse,
    AvailableYearsResponse,
    YearInfo
)
from api.services.annual_review_service import annual_review_service

router = APIRouter(prefix="/api/annual-review", tags=["annual-review"])


@router.get("/available-years", response_model=AvailableYearsResponse)
async def get_available_years():
    """
    Get list of available term/year combinations from Elasticsearch.
    
    Returns:
        AvailableYearsResponse: List of available years
    """
    try:
        years_data = annual_review_service.get_available_years()
        years = [YearInfo(**y) for y in years_data]
        return AvailableYearsResponse(years=years)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching available years: {str(e)}"
        )


@router.get("/data/{term}/{year}", response_model=AnnualReviewResponse)
async def get_annual_review(term: int, year: int):
    """
    Get annual review data for a specific term and year from Elasticsearch.
    
    Args:
        term: Parliamentary term number
        year: Year within the term
        
    Returns:
        AnnualReviewResponse: Complete annual review data
    """
    try:
        data = annual_review_service.get_annual_review(term, year)
        
        # Convert empty dicts to None for Optional fields
        for key in ['mostTalkedTopic', 'mostActiveMp', 'mostRepresentedProvince', 
                   'nicheTopic', 'decliningInterest', 'mostDiverseDebate']:
            if key in data and data[key] == {}:
                data[key] = None
        
        # Check if we got any valid data
        if not any(data.get(key) for key in ['mostTalkedTopic', 'mostActiveMp', 
                                             'mostRepresentedProvince', 'nicheTopic', 
                                             'decliningInterest', 'mostDiverseDebate']):
            raise HTTPException(
                status_code=404,
                detail=f"No data found for term {term}, year {year}"
            )
        
        return AnnualReviewResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching annual review data: {str(e)}"
        )

