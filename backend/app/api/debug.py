"""Debug endpoints — guarded by settings.debug, never exposed in production."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import get_db
from app.models.db import Design, DesignVariantRow, Session

settings = get_settings()
router = APIRouter(prefix="/debug", tags=["debug"])


class DebugVariantRequest(BaseModel):
    session_id: str | None = None
    image_url: str = "https://cdn.bobb.ai/test.png"
    prompt: str = "test prompt"
    style: str = "illustration"


@router.post("/variants", status_code=201)
async def create_debug_variant(
    body: DebugVariantRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Seed a variant for load/recovery testing. Disabled in production."""
    if not settings.debug:
        raise HTTPException(status_code=404)

    # Resolve or create a minimal session row
    if body.session_id:
        try:
            sid = uuid.UUID(body.session_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid session_id") from None
        session_row = await db.get(Session, sid)
        if session_row is None:
            session_row = Session(id=sid, current_state="greeting")
            db.add(session_row)
            await db.flush()
    else:
        session_row = Session(id=uuid.uuid4(), current_state="greeting")
        db.add(session_row)
        await db.flush()

    # Create a minimal Design stub to satisfy the FK
    design = Design(
        id=uuid.uuid4(),
        session_id=session_row.id,
        story_json={"debug": True},
        design_prompt_base=body.prompt,
    )
    db.add(design)
    await db.flush()

    variant = DesignVariantRow(
        id=uuid.uuid4(),
        design_id=design.id,
        variant_number=1,
        prompt_used=body.prompt,
        style=body.style,
        image_url=body.image_url,
        is_fallback=False,
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)

    return {
        "variant": {
            "id": str(variant.id),
            "design_id": str(variant.design_id),
            "session_id": str(session_row.id),
            "image_url": variant.image_url,
            "style": variant.style,
            "prompt_used": variant.prompt_used,
        }
    }
