"""Session endpoints — Sprint 0 stubs per api_contracts.md."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.services.session_manager import session_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", status_code=201)
async def create_session(db: AsyncSession = Depends(get_db)) -> dict:
    """Create a new customer session. Sprint 0: placeholder (no DB row yet)."""
    return session_manager.create_session()


@router.get("/{session_id}", status_code=501)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Get current session state. Sprint 1 implements DB lookup."""
    return {"detail": "Not implemented — Sprint 1"}
