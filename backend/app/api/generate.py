"""Image Generation endpoint.

POST /api/v1/sessions/{session_id}/generate
  - Accepts optional design_id (defaults to latest for the session)
  - Runs ImageGenerationService.generate_variants() for all 4 DesignStrategy variants
  - Persists DesignVariantRow records with prompt, seed, provider_request_id, image_url
  - Returns design_id + 4 variant objects

MockImageProvider is used by default; FalAIProvider is enabled when FAL_API_KEY is set.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.db import Design
from app.models.schemas import DesignStrategy
from app.services import session_manager
from app.services.design_service import get_design_with_variants, persist_variants
from app.services.image_gen import ImageGenerationService

router = APIRouter(prefix="/sessions", tags=["generate"])


class GenerateRequest(BaseModel):
    design_id: str | None = None  # use latest design for session if None
    seeds: list[int | None] | None = None  # optional per-variant seeds for deterministic replay


class VariantOut(BaseModel):
    variant_id: str
    variant_number: int
    style: str
    image_url: str | None
    generation_seed: int | None
    provider_request_id: str | None
    provider_name: str
    model_used: str
    generation_time_ms: int
    success: bool
    error: str | None


class GenerateResponse(BaseModel):
    design_id: str
    pipeline_run_id: str
    session_id: str
    variants: list[VariantOut]


@router.post("/{session_id}/generate")
async def generate_images(
    session_id: str,
    body: GenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GenerateResponse:
    """Generate 4 image variants from the session's DesignStrategy."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session_id format") from None

    session_row = await session_manager.get_session(db, sid)
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Resolve design_id
    design_id: uuid.UUID
    if body.design_id is not None:
        try:
            design_id = uuid.UUID(body.design_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid design_id format") from None
    else:
        resolved = await _get_latest_design_id(db, sid)
        if resolved is None:
            raise HTTPException(
                status_code=422,
                detail="No design found for this session. Call /design first.",
            )
        design_id = resolved

    # Load design and check it has a strategy
    design, _ = await get_design_with_variants(db, design_id)
    if design is None:
        raise HTTPException(status_code=404, detail="Design not found")
    if design.design_strategy_json is None:
        raise HTTPException(
            status_code=422,
            detail="Design has no strategy. Call /design first.",
        )

    strategy = DesignStrategy(**design.design_strategy_json)
    pipeline_run_id = design.pipeline_run_id or uuid.uuid4()

    # Get image provider from app.state
    image_provider = _get_image_provider(request)
    cache_root = (
        Path(request.app.state.cache_dir)
        if hasattr(request.app.state, "cache_dir")
        else Path("cache/designs")
    )

    svc = ImageGenerationService(provider=image_provider, cache_root=cache_root)
    variant_results = await svc.generate_variants(
        session_id=sid,
        variants=strategy.variants,
        seeds=body.seeds,
    )

    # Persist variant rows
    variant_ids = await persist_variants(
        db,
        design_id=design_id,
        pipeline_run_id=pipeline_run_id,
        variant_results=variant_results,
    )

    variants_out = [
        VariantOut(
            variant_id=str(vid),
            variant_number=vr.variant_number,
            style=vr.style,
            image_url=vr.result.image_url,
            generation_seed=vr.result.generation_seed,
            provider_request_id=vr.result.provider_request_id,
            provider_name=vr.result.provider_name,
            model_used=vr.result.model_used,
            generation_time_ms=vr.result.generation_time_ms,
            success=vr.result.success,
            error=vr.result.error,
        )
        for vid, vr in zip(
            variant_ids,
            sorted(variant_results, key=lambda x: x.variant_number), strict=False,
        )
    ]

    return GenerateResponse(
        design_id=str(design_id),
        pipeline_run_id=str(pipeline_run_id),
        session_id=session_id,
        variants=variants_out,
    )


async def _get_latest_design_id(
    db: AsyncSession, session_id: uuid.UUID
) -> uuid.UUID | None:
    result = await db.execute(
        select(Design)
        .where(Design.session_id == session_id)
        .where(Design.design_strategy_json.isnot(None))
        .order_by(Design.created_at.desc())
        .limit(1)
    )
    design = result.scalar_one_or_none()
    return design.id if design else None


def _get_image_provider(request: Request):  # type: ignore[return]
    provider = getattr(request.app.state, "image_provider", None)
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail="Image provider not configured.",
        )
    return provider
