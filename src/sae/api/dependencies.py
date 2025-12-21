"""API dependencies for authentication and authorization."""

import secrets
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException, Request, status

from sae.config import Settings, get_settings

logger = structlog.get_logger()


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


async def get_settings_dep() -> Settings:
    """Dependency to get application settings."""
    return get_settings()


async def verify_api_key(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    """Verify API key from request header.

    If API_KEY is not configured in settings, authentication is disabled
    and all requests are allowed.

    Args:
        request: FastAPI request object
        settings: Application settings
        x_api_key: API key from X-API-Key header

    Returns:
        The validated API key, or None if auth is disabled

    Raises:
        HTTPException: If authentication fails (401 Unauthorized)
    """
    # If no API key is configured, authentication is disabled
    if settings.api_key is None:
        return None

    # If API key is configured, require it in requests
    if x_api_key is None:
        logger.warning(
            "Missing API key",
            path=request.url.path,
            method=request.method,
            client=request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(x_api_key, settings.api_key):
        logger.warning(
            "Invalid API key",
            path=request.url.path,
            method=request.method,
            client=request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    return x_api_key


# Type alias for use in route dependencies
ApiKeyDep = Annotated[str | None, Depends(verify_api_key)]
