"""BOBB AI Platform — FastAPI application entrypoint.

Run with: uvicorn app.main:app --reload --port 8420
Production: uvicorn app.main:app --port 8420 --workers 1
(--workers 1 is REQUIRED: the WebSocket active_sessions registry is in-process.)
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import debug as debug_api
from app.api import design as design_api
from app.api import designs, orders, products, sessions, ws
from app.api import generate as generate_api
from app.api import recommendations as recommendations_api
from app.api import story as story_api
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.base import create_engine, create_session_factory

settings = get_settings()
configure_logging(debug=settings.debug)
logger = get_logger("main")


def _make_image_provider():  # type: ignore[no-untyped-def]
    """Build the image generation provider. MockImageProvider unless FAL_API_KEY set."""
    from app.services.image_gen import FalAIProvider, MockImageProvider
    if settings.fal_api_key:
        logger.info("image_provider", provider="fal_ai")
        return FalAIProvider(api_key=settings.fal_api_key)
    logger.info("image_provider", provider="mock")
    return MockImageProvider()


def _make_provider():  # type: ignore[no-untyped-def]
    """Build the LLM provider from settings. Returns None if no API key configured."""
    if not settings.anthropic_api_key:
        logger.warning(
            "no_anthropic_api_key",
            detail="Story Intelligence Agent disabled. Set ANTHROPIC_API_KEY to enable.",
        )
        return None
    from app.providers.anthropic import make_anthropic_provider
    return make_anthropic_provider(
        api_key=settings.anthropic_api_key,
        model="claude-sonnet-4-6",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # M-03: engine/session_factory on app.state for test isolation.
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    # LLM provider — None if ANTHROPIC_API_KEY not set (tests inject MockProvider).
    app.state.llm_provider = _make_provider()

    # Image provider — MockImageProvider by default; FalAIProvider when FAL_API_KEY set.
    app.state.image_provider = _make_image_provider()
    app.state.cache_dir = settings.cache_dir

    logger.info(
        "startup",
        port=settings.port,
        debug=settings.debug,
        llm_provider="anthropic" if app.state.llm_provider else "none",
    )
    yield
    await engine.dispose()
    logger.info("shutdown")


app = FastAPI(title="BOBB AI Platform", version="0.1.0", lifespan=lifespan)

# CORS: allow all for LAN dev (tablet on same network)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static mount for generated design images: GET /cache/designs/{session_id}/{file}
cache_root = Path(settings.cache_dir).parent
cache_root.mkdir(parents=True, exist_ok=True)
Path(settings.cache_dir).mkdir(parents=True, exist_ok=True)
app.mount("/cache", StaticFiles(directory=str(cache_root)), name="cache")

# API v1 routers
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(story_api.router, prefix="/api/v1")
app.include_router(design_api.router, prefix="/api/v1")
app.include_router(generate_api.router, prefix="/api/v1")
app.include_router(recommendations_api.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(designs.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(debug_api.router, prefix="/api/v1")
app.include_router(ws.router)


@app.get("/health")
async def health() -> dict:
    """Liveness check."""
    return {"status": "ok"}
