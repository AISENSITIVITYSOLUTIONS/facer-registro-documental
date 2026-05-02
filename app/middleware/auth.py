"""
API Key authentication dependency for FastAPI.

Usage:
    - Set the API_KEY environment variable to a strong secret.
    - Clients must include the header: Authorization: Bearer <API_KEY>
    - Routes that use the `api_key_auth` dependency will be protected.
    - If API_KEY is empty (development mode), authentication is skipped.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)


async def api_key_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """Validate the Bearer token against the configured API_KEY.

    Returns the validated API key string on success.
    Raises HTTP 401 if the key is missing or incorrect.
    Skips validation entirely when API_KEY is not configured (dev mode).
    """
    # Dev mode: if no API_KEY is set, skip authentication
    if not settings.api_key:
        return ""

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication. Include header: Authorization: Bearer <API_KEY>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
