"""Design persistence service.

Persists DesignStrategy to the designs table BEFORE any image generation (AW-17).
Keeps all SQL out of the agent and API layer.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Design
from app.models.schemas import DesignStrategy, Story


async def create_design_row(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    story: Story,
    strategy: DesignStrategy,
    pipeline_run_id: uuid.UUID,
    design_prompt_base: str,
    design_metadata_extra: dict[str, Any] | None = None,
) -> uuid.UUID:
    """Insert a new Design row with the strategy persisted before image generation.

    Returns the new design's UUID.
    """
    design_id = uuid.uuid4()
    await db.execute(
        insert(Design).values(
            id=design_id,
            session_id=session_id,
            story_json=story.model_dump(mode="json"),
            story_version=1,
            design_prompt_base=design_prompt_base,
            design_strategy_json=strategy.model_dump(mode="json"),
            design_metadata=design_metadata_extra,
            pipeline_run_id=pipeline_run_id,
            is_fallback=strategy.is_fallback,
        )
    )
    await db.commit()
    return design_id
