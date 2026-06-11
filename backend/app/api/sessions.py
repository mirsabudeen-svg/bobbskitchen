"""Session endpoints — Sprint 1: DB-backed session creation and lookup."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.services import session_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", status_code=201)
async def create_session(db: AsyncSession = Depends(get_db)) -> dict:
    """Create a new customer session and return the WebSocket path."""
    return await session_manager.create_session(db)


@router.get("/{session_id}")
async def get_session(
    session_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Get current session state."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session_id format") from None

    row = await session_manager.get_session(db, sid)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": str(row.id),
        "state": row.current_state,
        "created_at": row.created_at.isoformat().replace("+00:00", "Z"),
        "ws_path": f"/ws/{row.id}",
        "customer_name": row.customer_name,
        "completed": row.completed,
        "abandoned": row.abandoned,
    }
