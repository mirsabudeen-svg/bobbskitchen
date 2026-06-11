"""Design persistence service.

Persists DesignStrategy to the designs table BEFORE any image generation (AW-17).
Also persists DesignVariantRow records after generation completes.
Keeps all SQL out of the agent and API layer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Design, DesignVariantRow
from app.models.schemas import DesignStrategy, ProductRecommendation, Story
from app.services.image_gen import GenerationResult, VariantGenerationResult


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


async def persist_variants(
    db: AsyncSession,
    *,
    design_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    variant_results: list[VariantGenerationResult],
) -> list[uuid.UUID]:
    """Insert DesignVariantRow records for each generated variant.

    Returns list of variant UUIDs in variant_number order.
    Only inserts rows — does not commit; caller must commit if needed.
    (Called within a request handler that owns the transaction.)
    """
    variant_ids: list[uuid.UUID] = []
    for vr in sorted(variant_results, key=lambda x: x.variant_number):
        r = vr.result
        variant_id = uuid.uuid4()
        await db.execute(
            insert(DesignVariantRow).values(
                id=variant_id,
                design_id=design_id,
                variant_number=vr.variant_number,
                is_initial_set=True,
                prompt_used=r.image_path or "",  # placeholder if failed
                negative_prompt=None,
                style=vr.style,
                image_url=r.image_url,
                generation_time_ms=r.generation_time_ms,
                model_used=r.model_used,
                fal_request_id=r.provider_request_id,
                generation_seed=r.generation_seed,
                is_fallback=not r.success,
            )
        )
        variant_ids.append(variant_id)
    await db.commit()
    return variant_ids


async def get_design_with_variants(
    db: AsyncSession,
    design_id: uuid.UUID,
) -> tuple[Design | None, list[DesignVariantRow]]:
    """Fetch a Design and its initial variant rows."""
    design_result = await db.execute(
        select(Design).where(Design.id == design_id)
    )
    design = design_result.scalar_one_or_none()
    if design is None:
        return None, []

    variants_result = await db.execute(
        select(DesignVariantRow)
        .where(DesignVariantRow.design_id == design_id)
        .where(DesignVariantRow.is_initial_set.is_(True))
        .order_by(DesignVariantRow.variant_number)
    )
    variants = list(variants_result.scalars().all())
    return design, variants


async def get_variant(
    db: AsyncSession, variant_id: uuid.UUID
) -> DesignVariantRow | None:
    result = await db.execute(
        select(DesignVariantRow).where(DesignVariantRow.id == variant_id)
    )
    return result.scalar_one_or_none()


async def get_variant_history(
    db: AsyncSession, design_id: uuid.UUID
) -> list[DesignVariantRow]:
    """Return ALL variants for a design ordered by creation time.

    Includes both initial set (is_initial_set=True) and refined variants.
    The caller can reconstruct the full lineage tree using parent_variant_id.
    """
    result = await db.execute(
        select(DesignVariantRow)
        .where(DesignVariantRow.design_id == design_id)
        .order_by(DesignVariantRow.variant_number)
    )
    return list(result.scalars().all())


async def select_variant(
    db: AsyncSession,
    design_id: uuid.UUID,
    variant_id: uuid.UUID,
) -> None:
    """Set designs.selected_variant_id and mark the design as locked."""
    await db.execute(
        update(Design)
        .where(Design.id == design_id)
        .values(selected_variant_id=variant_id, design_locked=True)
    )
    await db.commit()


async def persist_refined_variant(
    db: AsyncSession,
    *,
    design_id: uuid.UUID,
    parent_variant_id: uuid.UUID,
    variant_number: int,
    style: str,
    refined_prompt: str,
    refined_negative: str,
    refinement_type: str,
    result: GenerationResult,
) -> uuid.UUID:
    """Insert a single refined variant row and increment design counters."""
    variant_id = uuid.uuid4()
    await db.execute(
        insert(DesignVariantRow).values(
            id=variant_id,
            design_id=design_id,
            variant_number=variant_number,
            is_initial_set=False,
            is_refined=True,
            prompt_used=refined_prompt,
            negative_prompt=refined_negative,
            style=style,
            image_url=result.image_url,
            generation_time_ms=result.generation_time_ms,
            model_used=result.model_used,
            fal_request_id=result.provider_request_id,
            generation_seed=result.generation_seed,
            is_fallback=not result.success,
            parent_variant_id=parent_variant_id,
            refinement_type=refinement_type,
        )
    )
    await db.execute(
        update(Design)
        .where(Design.id == design_id)
        .values(
            refinements_count=Design.refinements_count + 1,
            regenerations_count=Design.regenerations_count + 1,
        )
    )
    await db.commit()
    return variant_id


async def persist_recommendations(
    db: AsyncSession,
    *,
    design_id: uuid.UUID,
    recommendations: list[ProductRecommendation],
    model_used: str,
) -> None:
    """Persist top-3 recommendations into designs.recommendations_json."""
    await db.execute(
        update(Design)
        .where(Design.id == design_id)
        .values(
            recommendations_json=[r.model_dump(mode="json") for r in recommendations],
            recommendations_generated_at=datetime.now(UTC),
            recommendations_model=model_used,
        )
    )
    await db.commit()


async def get_recommendations(
    db: AsyncSession,
    design_id: uuid.UUID,
) -> list[ProductRecommendation] | None:
    """Return previously persisted recommendations, or None if not generated yet."""
    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()
    if design is None or design.recommendations_json is None:
        return None
    return [ProductRecommendation(**r) for r in design.recommendations_json]


async def next_variant_number(db: AsyncSession, design_id: uuid.UUID) -> int:
    """Return the next available variant number for a design."""
    result = await db.execute(
        select(DesignVariantRow.variant_number)
        .where(DesignVariantRow.design_id == design_id)
        .order_by(DesignVariantRow.variant_number.desc())
        .limit(1)
    )
    highest = result.scalar_one_or_none()
    return (highest or 0) + 1
