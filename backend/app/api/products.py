"""Product catalog endpoints — Sprint 0 stubs."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", status_code=501)
async def list_products(db: AsyncSession = Depends(get_db)) -> dict:
    """Full product catalog. Sprint 1 implements inventory query."""
    return {"detail": "Not implemented — Sprint 1"}
