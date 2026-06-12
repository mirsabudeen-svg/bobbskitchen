"""Session endpoints — Sprint 1: DB-backed session creation and lookup."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import asyncio

from app.db.base import get_db
from app.services import session_manager
from app.services.analytics import track_session_abandoned, track_session_started

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", status_code=201)
async def create_session(db: AsyncSession = Depends(get_db)) -> dict:
    """Create a new customer session and return the WebSocket path."""
    result = await session_manager.create_session(db)
    asyncio.create_task(track_session_started(db, result["session_id"]))
    return result


@router.post("/{session_id}/abandon")
async def abandon_session(
    session_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Mark a session as abandoned (idle timeout / customer walked away).

    Sprint 6.2 Fix 1: prevents the next customer's journey from running on
    the previous customer's session row.
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session_id format") from None

    row = await session_manager.get_session(db, sid)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    row.current_state = "idle"
    row.completed = False
    row.abandoned = True
    await db.commit()

    asyncio.create_task(track_session_abandoned(db, session_id))
    return {"abandoned": True, "session_id": session_id}


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
