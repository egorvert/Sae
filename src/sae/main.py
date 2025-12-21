"""Sae - A2A Legal Agent FastAPI Application."""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from sae import __version__
from sae.api.agent_card import router as agent_card_router
from sae.api.jsonrpc import router as jsonrpc_router
from sae.api.streaming import router as streaming_router
from sae.config import get_settings

# Create rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Sae Legal Agent",
        description="A2A-native legal agent for contract clause review and risk analysis",
        version=__version__,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # Rate limiting
    if settings.rate_limit_enabled:
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware - environment-aware
    cors_origins = settings.cors_origins
    if settings.is_production and cors_origins == ["*"]:
        logger.warning(
            "CORS wildcard in production - set CORS_ORIGINS env var to restrict access"
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )

    # Include routers
    app.include_router(agent_card_router)
    app.include_router(jsonrpc_router)
    app.include_router(streaming_router)

    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": __version__,
            "agent": settings.agent_name,
        }

    @app.on_event("startup")
    async def startup_event() -> None:
        """Log startup information."""
        logger.info(
            "Starting Sae Legal Agent",
            version=__version__,
            environment=settings.environment,
        )

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Clean up on shutdown."""
        logger.info("Shutting down Sae Legal Agent")

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "sae.main:app",
        host=settings.host,
        port=settings.port,
        reload=not settings.is_production,
    )
