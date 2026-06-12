"""Story Intelligence endpoint.

POST /api/v1/sessions/{session_id}/story
  - Accepts customer text input
  - Runs ConversationAgent.extract_story() with full prior turn history
  - Persists to conversation_logs and agent_logs
  - Returns structured Story + pipeline_run_id

The endpoint builds the provider from app.state so tests can inject MockProvider.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.conversation import ConversationAgent
from app.db.base import get_db
from app.models.db import ConversationLog
from app.models.schemas import ConversationTurn, Story
from app.services import session_manager
from app.services.agent_logger import log_agent_call, log_conversation_turn
from app.services.analytics import track_story_submitted

router = APIRouter(prefix="/sessions", tags=["story"])


class StoryRequest(BaseModel):
    text: str


class StoryResponse(BaseModel):
    pipeline_run_id: str
    session_id: str
    turn_number: int
    story: Story
    needs_clarification: bool
    clarification_question: str | None


@router.post("/{session_id}/story")
async def extract_story(
    session_id: str,
    body: StoryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StoryResponse:
    """Run the Conversation Agent on new customer input."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session_id format") from None

    row = await session_manager.get_session(db, sid)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Set story_started_at on first submission only — used for latency tracking
    if row.story_started_at is None:
        row.story_started_at = datetime.now(UTC)
        await db.commit()

    # Load prior conversation turns for multi-turn context reconstruction
    prior_turns = await _load_prior_turns(db, sid)
    turn_number = len(prior_turns) + 1

    pipeline_run_id = uuid.uuid4()

    provider = _get_provider(request)
    agent = ConversationAgent(provider=provider)

    start_ms = time.monotonic_ns() // 1_000_000
    try:
        story, meta = await agent.extract_story(
            new_input=body.text,
            prior_turns=prior_turns,
        )
    except Exception as exc:
        execution_ms = (time.monotonic_ns() // 1_000_000) - start_ms
        await log_agent_call(
            db,
            session_id=sid,
            pipeline_run_id=pipeline_run_id,
            agent_name="conversation",
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
        raise HTTPException(status_code=502, detail=f"Agent error: {exc}") from exc

    execution_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    # Persist conversation turn
    clarification_q = (
        story.clarification_questions[0] if story.clarification_questions else None
    )
    await log_conversation_turn(
        db,
        session_id=sid,
        turn_number=turn_number,
        customer_input=body.text,
        agent_response_json=None,
        agent_text_reply=clarification_q,
        story_extracted=story.model_dump(mode="json"),
        clarification_needed=story.needs_clarification,
        clarity_score=story.clarity_score,
        confidence=story.confidence,
        response_time_ms=execution_ms,
        tokens_input=meta["input_tokens"],
        tokens_output=meta["output_tokens"],
        model_used=meta["model_used"],
    )

    # Persist agent log
    await log_agent_call(
        db,
        session_id=sid,
        pipeline_run_id=pipeline_run_id,
        agent_name="conversation",
        model_used=meta["model_used"],
        state=row.current_state,
        prompt_version=meta["prompt_version"],
        tokens_input=meta["input_tokens"],
        tokens_output=meta["output_tokens"],
        execution_ms=execution_ms,
    )

    asyncio.create_task(
        track_story_submitted(
            db,
            session_id,
            story_word_count=len(body.text.split()),
            story_digest=body.text[:100],
        )
    )

    return StoryResponse(
        pipeline_run_id=str(pipeline_run_id),
        session_id=session_id,
        turn_number=turn_number,
        story=story,
        needs_clarification=story.needs_clarification,
        clarification_question=clarification_q,
    )


async def _load_prior_turns(
    db: AsyncSession, session_id: uuid.UUID
) -> list[ConversationTurn]:
    """Fetch all prior turns ordered by turn_number for history reconstruction."""
    result = await db.execute(
        select(ConversationLog)
        .where(ConversationLog.session_id == session_id)
        .order_by(ConversationLog.turn_number)
    )
    rows = result.scalars().all()
    return [
        ConversationTurn(
            turn_number=r.turn_number,
            customer_input=r.customer_input,
            agent_text_reply=r.agent_text_reply,
        )
        for r in rows
    ]


def _get_provider(request: Request) -> Any:
    """Get the LLM provider from app.state (injected at startup or in tests)."""
    provider = getattr(request.app.state, "llm_provider", None)
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail="LLM provider not configured. Set ANTHROPIC_API_KEY.",
        )
    return provider
