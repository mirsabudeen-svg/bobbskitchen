"""Design endpoints — Sprint 0 stubs."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db

router = APIRouter(prefix="/designs", tags=["designs"])


class DesignSelectRequest(BaseModel):
    variant_id: str  # UUID of design_variants row (FIX ISSUE-15)


@router.post("/{design_id}/select", status_code=501)
async def select_design_variant(
    design_id: str,
    body: DesignSelectRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Select a design variant. Sprint 3 implements."""
    return {"detail": "Not implemented — Sprint 3"}
