"""API routes for MP endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from api.models.schemas import MPListItem, MPDetailResponse, MPListResponse
from api.services.mp_service import mp_service

router = APIRouter(prefix="/api/mps", tags=["mps"])


@router.get("", response_model=MPListResponse)
async def list_mps(
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
    search: Optional[str] = Query(None, description="Search by MP name")
):
    """
    Get paginated list of MPs (without party info for performance).
    
    Use the detail endpoint to get full MP information including party history.
    """
    result = mp_service.get_all_mps_paginated(page=page, limit=limit, search=search)
    return MPListResponse(**result)


@router.get("/{mp_id}", response_model=MPDetailResponse)
async def get_mp_detail(mp_id: str):
    """Get detailed information about a specific MP."""
    mp_detail = mp_service.get_mp_detail(mp_id)
    
    if not mp_detail:
        raise HTTPException(status_code=404, detail=f"MP with id {mp_id} not found")
    
    return MPDetailResponse(id=mp_id, data=mp_detail)

