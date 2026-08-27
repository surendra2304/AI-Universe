"""Main FastAPI application entrypoint for AI Universe."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.friday_routes import friday_router
from app.api.routes import router as api_router
from app.config_production import production_config
from app.core.config import settings
from app.core.orchestrator import orchestrator
from app.health import health_router
from app.routers.ecosystem import ecosystem_router
from app.routers.enhanced_trading import enhanced_router
from app.routers.evolution_intel import evolution_router
from app.routers.live_intelligence import live_router
from app.routers.multi_market import multi_market_router
from app.routers.predictions import predictions_router
from app.routers.trading import router as trading_router
from app.security.api_security import ProductionSecurityMiddleware
from app.utils.logger import logger, setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events: startup and shutdown."""
    setup_logger(name="ai_universe", log_level=production_config.LOG_LEVEL)
    logger.info(
        "Starting %s in %s environment on %s:%d",
        production_config.APP_NAME,
        production_config.APP_ENV,
        production_config.HOST,
        production_config.PORT
    )
    # Initialize persistent SQLite memory database
    await orchestrator.memory.initialize()
    yield
    logger.info("Shutting down %s", production_config.APP_NAME)


app = FastAPI(
    title=production_config.APP_NAME,
    description="Local-first, provider-agnostic multi-agent intelligence platform with structured adversarial debate.",
    version="1.0.0",
    lifespan=lifespan
)

# Production security middleware (headers, rate limiting, payload bounding)
app.add_middleware(ProductionSecurityMiddleware)

# GZip response compression middleware for production efficiency
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS middleware for local frontend and developer UI tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled global exception on %s %s: %s", request.method, request.url, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error occurred.", "error_type": type(exc).__name__}
    )


# Mount API routes
app.include_router(health_router)
app.include_router(api_router)
app.include_router(friday_router)
app.include_router(trading_router)
app.include_router(enhanced_router)
app.include_router(live_router)
app.include_router(multi_market_router)
app.include_router(evolution_router)
app.include_router(predictions_router)
app.include_router(ecosystem_router)


@app.get("/")
async def root():
    """Root metadata endpoint."""
    return {
        "name": production_config.APP_NAME,
        "status": "online",
        "version": "1.0.0",
        "env": production_config.APP_ENV,
        "description": "Provider-agnostic multi-agent intelligence platform"
    }
