"""WebSocket endpoint /ws/{session_id}.

Sprint 0: accepts connection, sends session_resumed snapshot, handles ping/pong.
Sprint 5 adds full orchestration message routing.

NOTE: active_sessions is an in-process dict — backend MUST run with --workers 1.
"""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("ws")

# session_id -> WebSocket. In-process registry; not multi-worker safe.
active_sessions: dict[str, WebSocket] = {}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    is_reconnect = session_id in active_sessions
    active_sessions[session_id] = websocket
    logger.info("ws_connected", session_id=session_id, is_reconnect=is_reconnect)

    # FIX ISSUE-20: always send full session snapshot on connect.
    # Sprint 0: stub snapshot (greeting state, no design/recommendations/order).
    await websocket.send_json(
        {
            "type": "session_resumed",
            "session_id": session_id,
            "state": "greeting",
            "is_reconnect": is_reconnect,
            "session": {
                "created_at": _now(),
                "duration_seconds": 0,
                "customer_name": None,
            },
            "latest_design": None,
            "recommendations": None,
            "order": None,
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
                # Sprint 5 implements full message routing.
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
