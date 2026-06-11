"""Design Strategy endpoint.

POST /api/v1/sessions/{session_id}/design
  - Accepts story JSON (or fetches latest from conversation_logs)
  - Runs DesignAgent.generate_strategy()
  - Persists DesignStrategy to designs table (before image generation)
  - Logs to agent_logs
  - Returns DesignStrategyResponse with design_id and pipeline_run_id
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.design import DesignAgent
from app.db.base import get_db
from app.models.db import ConversationLog
from app.models.schemas import DesignStrategy, Story
from app.services import session_manager
from app.services.agent_logger import log_agent_call
from app.services.design_service import create_design_row

router = APIRouter(prefix="/sessions", tags=["design"])


class DesignRequest(BaseModel):
    story: Story | None = None  # if None, latest story from conversation_logs is used


class VariantPromptOut(BaseModel):
    style: str
    prompt: str
    negative_prompt: str
    color_palette: list[str]
    mood: str
    width: int
    height: int


class DesignMetadataOut(BaseModel):
    cultural_authenticity_score: float
    print_feasibility: str
    color_count: int
    complexity: str
    estimated_print_time_min: float
    kerala_themes_used: list[str]


class DesignStrategyOut(BaseModel):
    base_story_summary: str
    variants: list[VariantPromptOut]
    design_metadata: DesignMetadataOut
    is_fallback: bool


class DesignStrategyResponse(BaseModel):
    design_id: str
    pipeline_run_id: str
    session_id: str
    strategy: DesignStrategyOut
    primary_kerala_theme: str | None
    primary_emotion: str | None
    key_symbols: list[str]
    product_suitability: dict[str, float]


@router.post("/{session_id}/design")
async def generate_design_strategy(
    session_id: str,
    body: DesignRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DesignStrategyResponse:
    """Run the Design Agent on the session's story and persist the strategy."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session_id format") from None

    row = await session_manager.get_session(db, sid)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Resolve story — use provided or fetch latest extracted story from conversation_logs
    story = body.story
    if story is None:
        story = await _load_latest_story(db, sid)
    if story is None:
        raise HTTPException(
            status_code=422,
            detail="No story found for this session. Call /story first.",
        )

    pipeline_run_id = uuid.uuid4()

    provider = _get_provider(request)
    agent = DesignAgent(provider=provider)

    start_ms = time.monotonic_ns() // 1_000_000
    try:
        strategy, meta = await agent.generate_strategy(story=story)
    except Exception as exc:
        execution_ms = (time.monotonic_ns() // 1_000_000) - start_ms
        await log_agent_call(
            db,
            session_id=sid,
            pipeline_run_id=pipeline_run_id,
            agent_name="design",
            model_used="unknown",
            state=row.current_state,
            prompt_version=agent.prompt_version,
            tokens_input=0,
            tokens_output=0,
            execution_ms=execution_ms,
            success=False,
            error_code="AGENT_ERROR",
            error_message=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"Design agent error: {exc}") from exc

    execution_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    # Persist strategy BEFORE image generation (AW-17)
    design_id = await create_design_row(
        db,
        session_id=sid,
        story=story,
        strategy=strategy,
        pipeline_run_id=pipeline_run_id,
        design_prompt_base=strategy.base_story_summary,
        design_metadata_extra={
            "primary_kerala_theme": meta.get("primary_kerala_theme"),
            "primary_emotion": meta.get("primary_emotion"),
            "key_symbols": meta.get("key_symbols", []),
            "product_suitability": meta.get("product_suitability", {}),
        },
    )

    # Log agent call
    await log_agent_call(
        db,
        session_id=sid,
        pipeline_run_id=pipeline_run_id,
        agent_name="design",
        model_used=meta["model_used"],
        state=row.current_state,
        prompt_version=meta["prompt_version"],
        tokens_input=meta["input_tokens"],
        tokens_output=meta["output_tokens"],
        execution_ms=execution_ms,
    )

    return DesignStrategyResponse(
        design_id=str(design_id),
        pipeline_run_id=str(pipeline_run_id),
        session_id=session_id,
        strategy=_to_strategy_out(strategy),
        primary_kerala_theme=meta.get("primary_kerala_theme"),
        primary_emotion=meta.get("primary_emotion"),
        key_symbols=meta.get("key_symbols", []),
        product_suitability=meta.get("product_suitability", {}),
    )


async def _load_latest_story(
    db: AsyncSession, session_id: uuid.UUID
) -> Story | None:
    """Load the most recent extracted story from conversation_logs."""
    result = await db.execute(
        select(ConversationLog)
        .where(ConversationLog.session_id == session_id)
        .where(ConversationLog.story_extracted.isnot(None))
        .order_by(ConversationLog.turn_number.desc())
        .limit(1)
    )
    log_row = result.scalar_one_or_none()
    if log_row is None or log_row.story_extracted is None:
        return None
    try:
        return Story(**log_row.story_extracted)
    except Exception:
        return None


def _get_provider(request: Request) -> Any:
    provider = getattr(request.app.state, "llm_provider", None)
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail="LLM provider not configured. Set ANTHROPIC_API_KEY.",
        )
    return provider


def _to_strategy_out(strategy: DesignStrategy) -> DesignStrategyOut:
    return DesignStrategyOut(
        base_story_summary=strategy.base_story_summary,
        variants=[
            VariantPromptOut(
                style=v.style.value,
                prompt=v.prompt,
                negative_prompt=v.negative_prompt,
                color_palette=v.color_palette,
                mood=v.mood,
                width=v.width,
                height=v.height,
            )
            for v in strategy.variants
        ],
        design_metadata=DesignMetadataOut(
            cultural_authenticity_score=strategy.design_metadata.cultural_authenticity_score,
            print_feasibility=strategy.design_metadata.print_feasibility,
            color_count=strategy.design_metadata.color_count,
            complexity=strategy.design_metadata.complexity,
            estimated_print_time_min=strategy.design_metadata.estimated_print_time_min,
            kerala_themes_used=[t.value for t in strategy.design_metadata.kerala_themes_used],
        ),
        is_fallback=strategy.is_fallback,
    )
