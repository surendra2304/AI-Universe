"""Security utilities and authentication dependencies for AI Universe."""

import hmac
from typing import Optional
from fastapi import Header, HTTPException, Security, status

from app.core.config import settings
from app.utils.logger import logger


async def verify_friday_api_key(
    x_inference_api_key: Optional[str] = Header(None, alias="X-INFERENCE-API-KEY"),
    x_ai_universe_api_key: Optional[str] = Header(None, alias="X-AI-UNIVERSE-API-KEY"),
    x_friday_api_key: Optional[str] = Header(None, alias="X-FRIDAY-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Validates that the incoming request from FRIDAY or agents possesses the authorized API Key.
    Supports X-INFERENCE-API-KEY, X-AI-UNIVERSE-API-KEY, X-FRIDAY-API-Key, and Bearer token headers.
    """
    configured_key = settings.get_friday_api_key()
    if not configured_key:
        logger.error("INFERENCE_API_KEY is not configured on the server.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server security configuration error: Inference integration key not configured."
        )

    provided_key = x_inference_api_key or x_ai_universe_api_key or x_friday_api_key
    if not provided_key and authorization:
        if authorization.startswith("Bearer "):
            provided_key = authorization[7:].strip()
        else:
            provided_key = authorization.strip()

    if not provided_key:
        logger.warning("Unauthorized access attempt: Missing authentication header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing 'X-AI-UNIVERSE-API-KEY' or 'X-FRIDAY-API-Key' authentication header."
        )

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(provided_key.encode("utf-8"), configured_key.encode("utf-8")):
        logger.warning("Forbidden access attempt: Invalid API Key provided.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid AI Universe API Key."
        )

    return provided_key
