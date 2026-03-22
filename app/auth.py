"""
app/auth.py — API key authentication

Read-only endpoints (/health, /metrics, /processes) are open.
Write endpoints (POST/PATCH/DELETE on /alerts) require a valid API key
in the X-API-Key header.

Set the key via environment variable:
    export SENTINEL_API_KEY="your-secret-key"
"""

import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

SENTINEL_API_KEY = os.environ.get("SENTINEL_API_KEY")

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(key: str | None = Security(_header)) -> str:
    """FastAPI dependency — rejects requests without a valid API key."""
    if SENTINEL_API_KEY is None:
        # No key configured → auth disabled (dev mode)
        return "dev"
    if not key or key != SENTINEL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
    return key
