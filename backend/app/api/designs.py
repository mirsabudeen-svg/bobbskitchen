"""Design endpoints — Sprint 4.

POST /api/v1/designs/{design_id}/select  — select a variant; locks the design
POST /api/v1/designs/{design_id}/refine  — refine a variant; creates new child variant
GET  /api/v1/designs/{design_id}/history — full variant lineage for a design
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.db import DesignVariantRow
from app.services import ws_broadcast
from app.services.design_service import (
    get_design_with_variants,
    get_variant,
    get_variant_history,
    next_variant_number,
    persist_refined_variant,
    select_variant,
)
from app.services.image_gen import GenerationParams
from app.services.refinement import MAX_REFINEMENTS, RefinementType, build_refined_prompt

router = APIRouter(prefix="/designs", tags=["designs"])


# ---------------------------------------------------------------------------
# Shared response models
# ---------------------------------------------------------------------------


class VariantHistoryItem(BaseModel):
    variant_id: str
    variant_number: int
    style: str | None
    is_initial_set: bool
    is_refined: bool
    parent_variant_id: str | None
    refinement_type: str | None
    image_url: str | None
    generation_seed: int | None
    is_fallback: bool
    success: bool  # is_fallback=False → success=True


# ---------------------------------------------------------------------------
# SELECT endpoint
# ---------------------------------------------------------------------------


class SelectRequest(BaseModel):
    variant_id: str


class SelectResponse(BaseModel):
    design_id: str
    selected_variant_id: str
    design_locked: bool


@router.post("/{design_id}/select")
async def select_design_variant(
    design_id: str,
    body: SelectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SelectResponse:
    """Select a variant as the chosen design and lock the design for production."""
    did = _parse_uuid(design_id, "design_id")
    vid = _parse_uuid(body.variant_id, "variant_id")

    design, _ = await get_design_with_variants(db, did)
    if design is None:
        raise HTTPException(status_code=404, detail="Design not found")

    variant = await get_variant(db, vid)
    if variant is None or variant.design_id != did:
        raise HTTPException(
            status_code=404,
            detail="Variant not found or does not belong to this design",
        )

    if design.design_locked and design.selected_variant_id == vid:
        # Idempotent: already selected
        return SelectResponse(
            design_id=str(did),
            selected_variant_id=str(vid),
            design_locked=True,
        )

    await select_variant(db, design_id=did, variant_id=vid)

    # WS: notify client that a variant was selected
    session_id = str(design.session_id)
    await ws_broadcast.broadcast(
        session_id,
        {
            "type": "variant_selected",
            "design_id": str(did),
            "variant_id": str(vid),
            "style": variant.style,
        },
    )

    return SelectResponse(
        design_id=str(did),
        selected_variant_id=str(vid),
        design_locked=True,
    )


# ---------------------------------------------------------------------------
# REFINE endpoint
# ---------------------------------------------------------------------------


class RefineRequest(BaseModel):
    variant_id: str  # parent variant to refine
    refinement_type: RefinementType
    seed: int | None = None  # optional deterministic seed


class RefineResponse(BaseModel):
    design_id: str
    new_variant_id: str
    variant_number: int
    style: str | None
    image_url: str | None
    generation_seed: int | None
    refinement_type: str
    parent_variant_id: str
    refinements_used: int
    refinements_remaining: int
    success: bool
    error: str | None


@router.post("/{design_id}/refine")
async def refine_design_variant(
    design_id: str,
    body: RefineRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RefineResponse:
    """Generate a refined child variant from an existing variant.

    Creates a new DesignVariantRow (never overwrites the original).
    Increments designs.refinements_count. Refuses when limit is reached.
    """
    did = _parse_uuid(design_id, "design_id")
    parent_vid = _parse_uuid(body.variant_id, "variant_id")

    design, _ = await get_design_with_variants(db, did)
    if design is None:
        raise HTTPException(status_code=404, detail="Design not found")

    # Guard: refinement limit
    if design.refinements_count >= MAX_REFINEMENTS:
        raise HTTPException(
            status_code=422,
            detail=f"Refinement limit reached ({MAX_REFINEMENTS}). No further refinements allowed.",
        )

    parent = await get_variant(db, parent_vid)
    if parent is None or parent.design_id != did:
        raise HTTPException(
            status_code=404,
            detail="Parent variant not found or does not belong to this design",
        )

    # Build refined prompts
    refined_prompt, refined_negative = build_refined_prompt(
        original_prompt=parent.prompt_used,
        original_negative=parent.negative_prompt,
        refinement_type=body.refinement_type,
    )

    # Determine the next variant number (5, 6, 7…)
    new_variant_number = await next_variant_number(db, did)

    # Image provider
    image_provider = _get_image_provider(request)
    cache_root = (
        Path(request.app.state.cache_dir)
        if hasattr(request.app.state, "cache_dir")
        else Path("cache/designs")
    )
    output_dir = cache_root / str(design.session_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    # WS: notify client refinement has started
    session_id = str(design.session_id)
    await ws_broadcast.send_refinement_started(
        session_id=session_id,
        design_id=str(did),
        parent_variant_id=str(parent_vid),
        refinement_type=body.refinement_type.value,
    )

    params = GenerationParams(
        prompt=refined_prompt,
        negative_prompt=refined_negative,
        width=parent.style and _style_dims(parent.style)[0] or 4000,
        height=parent.style and _style_dims(parent.style)[1] or 4800,
        seed=body.seed,
    )
    gen_result = await image_provider.generate(
        params,
        output_dir=output_dir,
        variant_number=new_variant_number,
        session_id=design.session_id,
    )

    new_variant_id = await persist_refined_variant(
        db,
        design_id=did,
        parent_variant_id=parent_vid,
        variant_number=new_variant_number,
        style=parent.style or "illustration",
        refined_prompt=refined_prompt,
        refined_negative=refined_negative,
        refinement_type=body.refinement_type.value,
        result=gen_result,
    )

    refinements_used = design.refinements_count + 1
    refinements_remaining = MAX_REFINEMENTS - refinements_used

    # WS: notify client refinement is complete
    await ws_broadcast.send_refinement_complete(
        session_id=session_id,
        design_id=str(did),
        new_variant_id=str(new_variant_id),
        refinements_remaining=refinements_remaining,
    )

    return RefineResponse(
        design_id=str(did),
        new_variant_id=str(new_variant_id),
        variant_number=new_variant_number,
        style=parent.style,
        image_url=gen_result.image_url,
        generation_seed=gen_result.generation_seed,
        refinement_type=body.refinement_type.value,
        parent_variant_id=str(parent_vid),
        refinements_used=refinements_used,
        refinements_remaining=refinements_remaining,
        success=gen_result.success,
        error=gen_result.error,
    )


# ---------------------------------------------------------------------------
# HISTORY endpoint
# ---------------------------------------------------------------------------


class VariantHistoryResponse(BaseModel):
    design_id: str
    total_variants: int
    variants: list[VariantHistoryItem]


@router.get("/{design_id}/history")
async def get_design_history(
    design_id: str,
    db: AsyncSession = Depends(get_db),
) -> VariantHistoryResponse:
    """Return all variants for a design, including refined children, ordered by variant_number."""
    did = _parse_uuid(design_id, "design_id")
    design, _ = await get_design_with_variants(db, did)
    if design is None:
        raise HTTPException(status_code=404, detail="Design not found")

    all_variants = await get_variant_history(db, did)
    return VariantHistoryResponse(
        design_id=str(did),
        total_variants=len(all_variants),
        variants=[_variant_to_item(v) for v in all_variants],
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


def _get_image_provider(request: Request):  # type: ignore[return]
    provider = getattr(request.app.state, "image_provider", None)
    if provider is None:
        raise HTTPException(
            status_code=503, detail="Image provider not configured."
        )
    return provider


def _style_dims(style: str) -> tuple[int, int]:
    """Default pixel dimensions per style; all standard shirt size for Sprint 4."""
    return 4000, 4800


def _variant_to_item(v: DesignVariantRow) -> VariantHistoryItem:
    return VariantHistoryItem(
        variant_id=str(v.id),
        variant_number=v.variant_number,
        style=v.style,
        is_initial_set=v.is_initial_set,
        is_refined=v.is_refined,
        parent_variant_id=str(v.parent_variant_id) if v.parent_variant_id else None,
        refinement_type=v.refinement_type,
        image_url=v.image_url,
        generation_seed=v.generation_seed,
        is_fallback=v.is_fallback,
        success=not v.is_fallback,
    )
