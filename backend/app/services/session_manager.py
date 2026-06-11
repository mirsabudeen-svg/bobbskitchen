"""SessionManager service — Sprint 0 stub.

Sprint 1 wires this to the database with validated state transitions.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.models.schemas import SessionState

# Valid state transitions (architecture.md). Used by Sprint 1 transition logic.
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


class SessionManager:
    """Sprint 0: in-memory placeholder. Sprint 1 replaces with DB-backed CRUD."""

    def create_session(self) -> dict[str, Any]:
        session_id = str(uuid.uuid4())
        return {
            "session_id": session_id,
            "state": SessionState.GREETING.value,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "ws_path": f"/ws/{session_id}",
        }


session_manager = SessionManager()
