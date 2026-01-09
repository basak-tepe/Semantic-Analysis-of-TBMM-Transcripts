"""Simple API key authentication middleware (optional)."""
import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

# API key from environment variable
API_KEY = os.getenv("API_KEY", None)

# If no API key is set, authentication is disabled
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verify API key if authentication is enabled.
    
    To enable authentication:
    1. Set API_KEY environment variable when deploying
    2. Users must include X-API-Key header in requests
    
    If API_KEY is not set, all requests are allowed (current behavior).
    """
    # If no API key is configured, allow all requests
    if API_KEY is None:
        return True
    
    # If API key is configured, verify it
    if api_key is None or api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key"
        )
    
    return True
