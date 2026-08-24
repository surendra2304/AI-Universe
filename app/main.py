"""Main FastAPI application entrypoint for AI Universe."""

from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Local-first, provider-agnostic multi-agent intelligence platform.",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "status": "online",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_env": settings.APP_ENV
    }
