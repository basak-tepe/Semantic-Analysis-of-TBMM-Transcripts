"""API routes for t-SNE endpoints."""
from fastapi import APIRouter, HTTPException

from api.models.tsne_schemas import WordsResponse, TSNEDataResponse
from api.services.tsne_service import tsne_service

router = APIRouter(prefix="/api/tsne", tags=["tsne"])


@router.get("/words", response_model=WordsResponse)
async def list_words():
    """Get list of available words for t-SNE visualizations."""
    words = tsne_service.get_available_words()
    return WordsResponse(words=words)


@router.get("/{word}", response_model=TSNEDataResponse)
async def get_tsne_data(word: str):
    """Get all t-SNE coordinate data points for a specific word."""
    data = tsne_service.get_tsne_data_for_word(word)
    
    if not data:
        # Check if word exists but has no data, or word doesn't exist
        available_words = tsne_service.get_available_words()
        if word not in available_words:
            raise HTTPException(
                status_code=404, 
                detail=f"Word '{word}' not found. Available words: {', '.join(available_words)}"
            )
        # Word exists but no data found
        return TSNEDataResponse(word=word, data=[])
    
    return TSNEDataResponse(word=word, data=data)

