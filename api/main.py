"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import CORS_ORIGINS
from api.routes import mps, tsne, annual_review

app = FastAPI(
    title="TBMM MP Analysis API",
    description="API for Member of Parliament analysis data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(mps.router)
app.include_router(tsne.router)
app.include_router(annual_review.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "TBMM MP Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "list_mps": "/api/mps",
            "mp_detail": "/api/mps/{mp_id}",
            "list_words": "/api/tsne/words",
            "tsne_images": "/api/tsne/{word}",
            "tsne_data": "/api/tsne/data/{word}",
            "annual_review_years": "/api/annual-review/available-years",
            "annual_review_data": "/api/annual-review/data/{term}/{year}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from api.services.elasticsearch_service import es_service
    es_connected = es_service.test_connection()
    
    return {
        "status": "healthy",
        "elasticsearch": "connected" if es_connected else "disconnected"
    }

