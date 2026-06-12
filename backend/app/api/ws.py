"""WebSocket endpoint /ws/{session_id}.

Sends a full session_resumed snapshot on connect, loaded from PostgreSQL:
  - session row (state, customer_name, duration_seconds)
  - latest design + initial variants
  - recommendations_json (if generated)
  - order (None in MVP)

Handles ping/pong. All other server-push events (generation_started,
variant_ready, refinement_complete, etc.) arrive via ws_broadcast helpers
called from the HTTP handlers.

NOTE: active_sessions is an in-process dict — backend MUST run with --workers 1.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.logging import get_logger
from app.models.db import Design, DesignVariantRow
from app.models.db import Session as SessionRow

router = APIRouter()
logger = get_logger("ws")

# session_id (str) -> WebSocket. In-process registry; not multi-worker safe.
active_sessions: dict[str, WebSocket] = {}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


async def _load_session_snapshot(
    websocket: WebSocket,
    session_id: str,
) -> dict[str, Any]:
    """Query PostgreSQL for the current session + design + recommendations state.

    Opens a scoped DB session that is closed immediately after the query so the
    WebSocket connection does not hold a pool connection for its entire lifetime.
    Falls back to a minimal greeting snapshot if the session_id is unknown.
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return _greeting_snapshot()

    factory = websocket.app.state.session_factory
    async with factory() as db:
        sess_result = await db.execute(
            select(SessionRow).where(SessionRow.id == sid)
        )
        session = sess_result.scalar_one_or_none()
        if session is None:
            return _greeting_snapshot()

        design_result = await db.execute(
            select(Design)
            .where(Design.session_id == sid)
            .order_by(Design.created_at.desc())
            .limit(1)
        )
        design = design_result.scalar_one_or_none()

        latest_design = None
        recommendations = None

        if design is not None:
            variants_result = await db.execute(
                select(DesignVariantRow)
                .where(DesignVariantRow.design_id == design.id)
                .where(DesignVariantRow.is_initial_set.is_(True))
                .order_by(DesignVariantRow.variant_number)
            )
            variants = list(variants_result.scalars().all())

            latest_design = {
                "design_id": str(design.id),
                "variants": [
                    {
                        "variant_id": str(v.id),
                        "variant_number": v.variant_number,
                        "style": v.style,
                        "image_url": v.image_url,
                        "is_refined": v.is_refined,
                    }
                    for v in variants
                ],
                "selected_variant_id": (
                    str(design.selected_variant_id)
                    if design.selected_variant_id
                    else None
                ),
                "refinements_count": design.refinements_count,
                "design_locked": design.design_locked,
            }

            if design.recommendations_json:
                recommendations = design.recommendations_json

    # Infer the screen the customer was on from persisted data
    state = _infer_state(session, latest_design, recommendations)

    return {
        "state": state,
        "session": {
            "created_at": session.created_at.isoformat().replace("+00:00", "Z"),
            "duration_seconds": session.duration_seconds or 0,
            "customer_name": session.customer_name,
        },
        "latest_design": latest_design,
        "recommendations": recommendations,
        "order": None,
    }


def _infer_state(
    session: SessionRow,
    latest_design: dict[str, Any] | None,
    recommendations: list[dict[str, Any]] | None,
) -> str:
    """Pick the most appropriate screen state based on persisted data.

    State inference priority (most advanced first):
    1. Recommendations exist → product_selection
    2. Variants generated → preview
    3. Design strategy exists (no variants) → generating
    4. Session DB state (usually greeting for new sessions)
    """
    if recommendations:
        return "product_selection"
    if latest_design and latest_design.get("variants"):
        return "preview"
    if latest_design:
        return "generating"
    return session.current_state


def _greeting_snapshot() -> dict[str, Any]:
    return {
        "state": "greeting",
        "session": {
            "created_at": _now(),
            "duration_seconds": 0,
            "customer_name": None,
        },
        "latest_design": None,
        "recommendations": None,
        "order": None,
    }


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    is_reconnect = session_id in active_sessions
    active_sessions[session_id] = websocket
    logger.info("ws_connected", session_id=session_id, is_reconnect=is_reconnect)

    snapshot = await _load_session_snapshot(websocket, session_id)
    await websocket.send_json(
        {
            "type": "session_resumed",
            "session_id": session_id,
            "is_reconnect": is_reconnect,
            **snapshot,
        }
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "INVALID_STATE",
                        "message": "Malformed JSON message",
                        "recoverable": False,
                        "suggested_action": "reconnect",
                    }
                )
                continue

            msg_type = message.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": _now()})
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "INVALID_STATE",
                        "message": f"Message type '{msg_type}' not implemented yet",
                        "recoverable": True,
                        "suggested_action": "retry",
                    }
                )
    except WebSocketDisconnect:
        logger.info("ws_disconnected", session_id=session_id)
    finally:
        if active_sessions.get(session_id) is websocket:
            del active_sessions[session_id]
