"""SessionManager — Sprint 1: DB-backed session CRUD with state machine validation.

State transitions are validated server-side; invalid transitions raise
InvalidStateTransition which the WebSocket handler maps to an error message.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Session as SessionRow
from app.models.schemas import SessionState

# Valid transitions from architecture.md
STATE_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.IDLE: {SessionState.GREETING},
    SessionState.GREETING: {SessionState.LISTENING},
    SessionState.LISTENING: {SessionState.THINKING, SessionState.CLARIFYING},
    SessionState.CLARIFYING: {SessionState.LISTENING, SessionState.THINKING},
    SessionState.THINKING: {SessionState.GENERATING},
    SessionState.GENERATING: {SessionState.PREVIEW},
    SessionState.PREVIEW: {SessionState.REFINING, SessionState.THINKING},
    SessionState.REFINING: {SessionState.GENERATING, SessionState.PRODUCT_SELECTION},
    SessionState.PRODUCT_SELECTION: {SessionState.CART},
    SessionState.CART: {SessionState.PRODUCT_SELECTION, SessionState.CHECKOUT},
    SessionState.CHECKOUT: {SessionState.PRODUCTION},
    SessionState.PRODUCTION: {SessionState.SUCCESS, SessionState.ERROR},
    SessionState.SUCCESS: {SessionState.IDLE},
    SessionState.ERROR: {SessionState.IDLE, SessionState.HELP},
    SessionState.HELP: {SessionState.IDLE},
}


class InvalidStateTransition(Exception):
    pass


class SessionNotFound(Exception):
    pass


async def create_session(db: AsyncSession) -> dict[str, Any]:
    """Create a new session row in the DB. Returns the api_contracts.md shape."""
    session_id = uuid.uuid4()
    now = datetime.now(UTC)
    row = SessionRow(
        id=session_id,
        created_at=now,
        updated_at=now,
        current_state=SessionState.GREETING.value,
    )
    db.add(row)
    await db.commit()
    return {
        "session_id": str(session_id),
        "state": SessionState.GREETING.value,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "ws_path": f"/ws/{session_id}",
    }


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> SessionRow | None:
    result = await db.execute(
        select(SessionRow).where(SessionRow.id == session_id)
    )
    return result.scalar_one_or_none()


async def transition_state(
    db: AsyncSession,
    session_id: uuid.UUID,
    new_state: SessionState,
) -> SessionRow:
    """Validate and apply a state transition. Raises InvalidStateTransition on bad input."""
    row = await get_session(db, session_id)
    if row is None:
        raise SessionNotFound(str(session_id))

    current = SessionState(row.current_state)
    allowed = STATE_TRANSITIONS.get(current, set())
    if new_state not in allowed:
        raise InvalidStateTransition(
            f"{current.value} → {new_state.value} is not a valid transition. "
            f"Allowed from {current.value}: {[s.value for s in allowed]}"
        )

    await db.execute(
        update(SessionRow)
        .where(SessionRow.id == session_id)
        .values(
            current_state=new_state.value,
            updated_at=datetime.now(UTC),
        )
    )
    await db.commit()
    row.current_state = new_state.value
    return row
