"""Product Recommendation endpoints — Sprint 5.

POST /api/v1/designs/{design_id}/recommend
  - Loads Story + DesignStrategy from DB
  - Runs ProductAgent.recommend() against PRODUCT_REGISTRY
  - Persists top-3 to designs.recommendations_json
  - Logs to agent_logs
  - Returns ranked ProductRecommendation list

GET /api/v1/designs/{design_id}/recommendations
  - Returns previously persisted recommendations (no re-run)
  - 404 if design not found
  - 422 if recommendations not yet generated
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.product import ProductAgent
from app.db.base import get_db
from app.models.schemas import (
    DesignStrategy,
    ProductRecommendation,
    Story,
)
from app.services.agent_logger import log_agent_call
from app.services.design_service import (
    get_design_with_variants,
    get_recommendations,
    persist_recommendations,
)

router = APIRouter(prefix="/designs", tags=["recommendations"])


# ---------------------------------------------------------------------------
# Response models (serialised form of ProductRecommendation)
# ---------------------------------------------------------------------------


class ScoreBreakdownOut(BaseModel):
    design_fit: float
    complexity_match: float
    inferred_demographics: float
    budget_fit: float
    inventory_available: bool


class MockupHintOut(BaseModel):
    suggested_color: str
    suggested_size: str | None
    placement: str | None


class ProductRecommendationOut(BaseModel):
    rank: int
    product_id: str
    product_name: str
    score: float
    score_breakdown: ScoreBreakdownOut
    reasons: list[str]
    price_paise: int
    price_rupees: float  # convenience field for UI
    print_area_width_in: float
    print_area_height_in: float
    production_time_minutes: int
    mockup_hint: MockupHintOut
    units_available: int
    low_stock: bool  # units_available < 5


class RecommendationResponse(BaseModel):
    design_id: str
    pipeline_run_id: str
    recommendations: list[ProductRecommendationOut]
    model_used: str


class RecommendationListResponse(BaseModel):
    design_id: str
    recommendations: list[ProductRecommendationOut]
    generated_at: str | None


# ---------------------------------------------------------------------------
# POST /recommend
# ---------------------------------------------------------------------------


@router.post("/{design_id}/recommend")
async def generate_recommendations(
    design_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """Run ProductAgent and persist top-3 recommendations for this design."""
    did = _parse_uuid(design_id, "design_id")

    design, _ = await get_design_with_variants(db, did)
    if design is None:
        raise HTTPException(status_code=404, detail="Design not found")
    if design.design_strategy_json is None:
        raise HTTPException(
            status_code=422,
            detail="Design has no strategy. Call /design first.",
        )
    if design.story_json is None:
        raise HTTPException(
            status_code=422,
            detail="Design has no story. Call /story first.",
        )

    try:
        story = Story(**design.story_json)
        strategy = DesignStrategy(**design.design_strategy_json)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Stored design data is invalid: {exc}"
        ) from exc

    pipeline_run_id = design.pipeline_run_id or uuid.uuid4()
    provider = _get_provider(request)
    agent = ProductAgent(provider=provider)

    start_ms = time.monotonic_ns() // 1_000_000
    try:
        recs, meta = await agent.recommend(story=story, strategy=strategy)
    except Exception as exc:
        execution_ms = (time.monotonic_ns() // 1_000_000) - start_ms
        await log_agent_call(
            db,
            session_id=design.session_id,
            pipeline_run_id=pipeline_run_id,
            agent_name="product",
            model_used="unknown",
            state="product_selection",
            prompt_version=agent.prompt_version,
            tokens_input=0,
            tokens_output=0,
            execution_ms=execution_ms,
            success=False,
            error_code="AGENT_ERROR",
            error_message=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"Product agent error: {exc}") from exc

    execution_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    await persist_recommendations(
        db,
        design_id=did,
        recommendations=recs,
        model_used=meta["model_used"],
    )

    await log_agent_call(
        db,
        session_id=design.session_id,
        pipeline_run_id=pipeline_run_id,
        agent_name="product",
        model_used=meta["model_used"],
        state="product_selection",
        prompt_version=meta["prompt_version"],
        tokens_input=meta["input_tokens"],
        tokens_output=meta["output_tokens"],
        execution_ms=execution_ms,
    )

    return RecommendationResponse(
        design_id=str(did),
        pipeline_run_id=str(pipeline_run_id),
        recommendations=[_to_out(r) for r in recs],
        model_used=meta["model_used"],
    )


# ---------------------------------------------------------------------------
# GET /recommendations
# ---------------------------------------------------------------------------


@router.get("/{design_id}/recommendations")
async def get_design_recommendations(
    design_id: str,
    db: AsyncSession = Depends(get_db),
) -> RecommendationListResponse:
    """Return previously persisted recommendations without re-running the agent."""
    did = _parse_uuid(design_id, "design_id")

    design, _ = await get_design_with_variants(db, did)
    if design is None:
        raise HTTPException(status_code=404, detail="Design not found")

    recs = await get_recommendations(db, did)
    if recs is None:
        raise HTTPException(
            status_code=422,
            detail="Recommendations not yet generated. Call POST /recommend first.",
        )

    generated_at = (
        design.recommendations_generated_at.isoformat().replace("+00:00", "Z")
        if design.recommendations_generated_at
        else None
    )

    return RecommendationListResponse(
        design_id=str(did),
        recommendations=[_to_out(r) for r in recs],
        generated_at=generated_at,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"Invalid {field_name} format"
        ) from None


def _get_provider(request: Request) -> Any:
    provider = getattr(request.app.state, "llm_provider", None)
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail="LLM provider not configured. Set ANTHROPIC_API_KEY.",
        )
    return provider


def _to_out(r: ProductRecommendation) -> ProductRecommendationOut:
    return ProductRecommendationOut(
        rank=r.rank,
        product_id=r.product_id,
        product_name=r.product_name,
        score=r.score,
        score_breakdown=ScoreBreakdownOut(
            design_fit=r.score_breakdown.design_fit,
            complexity_match=r.score_breakdown.complexity_match,
            inferred_demographics=r.score_breakdown.inferred_demographics,
            budget_fit=r.score_breakdown.budget_fit,
            inventory_available=r.score_breakdown.inventory_available,
        ),
        reasons=r.reasons,
        price_paise=r.price_paise,
        price_rupees=r.price_paise / 100,
        print_area_width_in=r.print_area_width_in,
        print_area_height_in=r.print_area_height_in,
        production_time_minutes=r.production_time_minutes,
        mockup_hint=MockupHintOut(
            suggested_color=r.mockup_hint.suggested_color,
            suggested_size=r.mockup_hint.suggested_size,
            placement=r.mockup_hint.placement,
        ),
        units_available=r.units_available,
        low_stock=r.units_available < 5,
    )
