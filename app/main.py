"""Main FastAPI application entrypoint for AI Universe."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router as api_router
from app.core.config import settings
from app.core.orchestrator import orchestrator
from app.utils.logger import logger, setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events: startup and shutdown."""
    # Initialize application logger on startup
    setup_logger(name="ai_universe", log_level=settings.LOG_LEVEL)
    logger.info(
        "Starting %s in %s environment on %s:%d",
        settings.APP_NAME,
        settings.APP_ENV,
        settings.HOST,
        settings.PORT
    )
    # Initialize persistent SQLite memory database
    await orchestrator.memory.initialize()
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="Local-first, provider-agnostic multi-agent intelligence platform.",
    version="0.1.0",
    lifespan=lifespan
)

# Mount API routes
app.include_router(api_router)


@app.get("/")
async def root():
    """Root metadata endpoint."""
    return {
        "name": settings.APP_NAME,
        "status": "online",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
