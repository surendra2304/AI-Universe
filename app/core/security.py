"""Security utilities and authentication dependencies for AI Universe."""

import hmac
from typing import Optional
from fastapi import Header, HTTPException, Security, status

from app.core.config import settings
from app.utils.logger import logger


async def verify_friday_api_key(
    x_friday_api_key: Optional[str] = Header(None, alias="X-FRIDAY-API-Key")
) -> str:
    """
    Validates that the incoming request from FRIDAY possesses the authorized API Key.
    Enforces security boundary between FRIDAY and AI Universe.
    """
    configured_key = settings.FRIDAY_API_KEY
    if not configured_key:
        logger.error("FRIDAY_API_KEY is not configured on the server.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server security configuration error: FRIDAY integration key not configured."
        )

    if not x_friday_api_key:
        logger.warning("Unauthorized access attempt to FRIDAY endpoint: Missing X-FRIDAY-API-Key header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing 'X-FRIDAY-API-Key' authentication header."
        )

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(x_friday_api_key.encode("utf-8"), configured_key.encode("utf-8")):
        logger.warning("Forbidden access attempt to FRIDAY endpoint: Invalid API Key provided.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid FRIDAY API Key."
        )

    return x_friday_api_key
