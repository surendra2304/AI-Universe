"""Security utilities and authentication dependencies for Inference."""

import hmac

from fastapi import Header, HTTPException, status

from app.core.config import settings
from app.utils.logger import logger


async def verify_friday_api_key(
    x_inference_api_key: str | None = Header(None, alias="X-INFERENCE-API-KEY"),
    x_friday_api_key: str | None = Header(None, alias="X-FRIDAY-API-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> str:
    """
    Validates that the incoming request from FRIDAY or agents possesses the authorized API Key.
    Supports X-INFERENCE-API-KEY, X-Inference-API-KEY, X-FRIDAY-API-Key, and Bearer token headers.
    """
    configured_key = settings.get_friday_api_key()
    if not configured_key:
        if settings.INSECURE_DEV_AUTH:
            logger.warning("INSECURE_DEV_AUTH is enabled; bypassing integration authentication.")
            return "dev_insecure_key"
        logger.error("INFERENCE_API_KEY is not configured on the server.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server security configuration error: Inference integration key not configured."
        )

    provided_key = x_inference_api_key or x_friday_api_key
    if not provided_key and authorization:
        if authorization.startswith("Bearer "):
            provided_key = authorization[7:].strip()
        else:
            provided_key = authorization.strip()

    if not provided_key:
        logger.warning("Unauthorized access attempt: Missing authentication header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing 'X-Inference-API-KEY' or 'X-FRIDAY-API-Key' authentication header."
        )

    valid_keys = [
        k for k in [
            settings.INFERENCE_API_KEY,
            settings.inference_api_KEY,
            settings.FRIDAY_UNIVERSE_API_KEY,
            settings.X_FRIDAY_API_KEY,
            settings.FRIDAY_API_KEY,
        ] if k
    ]

    # Constant-time comparison to prevent timing attacks against configured ecosystem keys
    if not any(hmac.compare_digest(provided_key.encode("utf-8"), vk.encode("utf-8")) for vk in valid_keys):
        logger.warning("Forbidden access attempt: Invalid API Key provided.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid API Key provided."
        )

    return provided_key
