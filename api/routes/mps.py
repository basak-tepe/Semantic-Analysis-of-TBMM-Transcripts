"""API routes for MP endpoints."""
from fastapi import APIRouter, HTTPException
from typing import List

from api.models.schemas import MPListItem, MPDetailResponse, MPListResponse
from api.services.mp_service import mp_service

router = APIRouter(prefix="/api/mps", tags=["mps"])


@router.get("", response_model=MPListResponse)
async def list_mps():
    """Get list of all MPs."""
    mps = mp_service.get_all_mps()
    return MPListResponse(mps=[MPListItem(**mp) for mp in mps])


@router.get("/{mp_id}", response_model=MPDetailResponse)
async def get_mp_detail(mp_id: str):
    """Get detailed information about a specific MP."""
    mp_detail = mp_service.get_mp_detail(mp_id)
    
    if not mp_detail:
        raise HTTPException(status_code=404, detail=f"MP with id {mp_id} not found")
    
    return MPDetailResponse(id=mp_id, data=mp_detail)

