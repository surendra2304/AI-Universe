"""Main FastAPI application entrypoint for AI Universe."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    description="Local-first, provider-agnostic multi-agent intelligence platform with structured adversarial debate.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for local frontend and developer UI tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled global exception on %s %s: %s", request.method, request.url, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error occurred.", "error_type": type(exc).__name__}
    )

# Mount API routes
app.include_router(api_router)


@app.get("/")
async def root():
    """Root metadata endpoint."""
    return {
        "name": settings.APP_NAME,
        "status": "online",
        "version": "1.0.0",
        "description": "Provider-agnostic multi-agent intelligence platform"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
