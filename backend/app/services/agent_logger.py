"""Persist agent call metadata to agent_logs and conversation_logs.

Called by the orchestrator / API layer after every agent invocation.
Keeps all SQL out of the agent itself (agents are pure LLM logic).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import AgentLog, ConversationLog


async def log_agent_call(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    agent_name: str,
    model_used: str,
    state: str,
    prompt_version: str,
    tokens_input: int,
    tokens_output: int,
    execution_ms: int,
    success: bool = True,
    is_fallback: bool = False,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    """Insert one row into agent_logs."""
    cost = _estimate_cost_microdollars(agent_name, tokens_input, tokens_output)
    await db.execute(
        insert(AgentLog).values(
            session_id=session_id,
            pipeline_run_id=pipeline_run_id,
            agent_name=agent_name,
            model_used=model_used,
            state=state,
            prompt_version=prompt_version,
            is_fallback=is_fallback,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_microdollars=cost,
            execution_ms=execution_ms,
            success=success,
            error_code=error_code,
            error_message=error_message,
        )
    )
    await db.commit()


async def log_conversation_turn(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    turn_number: int,
    customer_input: str,
    agent_response_json: str | None,
    agent_text_reply: str | None,
    story_extracted: dict[str, Any] | None,
    clarification_needed: bool,
    clarity_score: float | None,
    confidence: float | None,
    response_time_ms: int,
    tokens_input: int,
    tokens_output: int,
    model_used: str,
) -> uuid.UUID:
    """Insert one row into conversation_logs. Returns the new row's UUID."""
    row_id = uuid.uuid4()
    await db.execute(
        insert(ConversationLog).values(
            id=row_id,
            session_id=session_id,
            turn_number=turn_number,
            input_type="text",
            customer_input=customer_input,
            agent_response=agent_response_json,
            agent_text_reply=agent_text_reply,
            story_extracted=story_extracted,
            clarification_needed=clarification_needed,
            clarity_score=clarity_score,
            confidence=confidence,
            response_time_ms=response_time_ms,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            model_used=model_used,
        )
    )
    await db.commit()
    return row_id


def _estimate_cost_microdollars(
    agent_name: str, tokens_input: int, tokens_output: int
) -> int:
    """Rough cost estimate in microdollars (1 USD = 1_000_000 microdollars).

    Rates as of 2025 (Sonnet 4.6 / Haiku 4.5):
    - sonnet: $3/M input, $15/M output
    - haiku:  $0.80/M input, $4/M output
    """
    if agent_name == "product":
        input_rate = 0.80 / 1_000_000
        output_rate = 4.00 / 1_000_000
    else:
        input_rate = 3.00 / 1_000_000
        output_rate = 15.00 / 1_000_000
    usd = tokens_input * input_rate + tokens_output * output_rate
    return round(usd * 1_000_000)
