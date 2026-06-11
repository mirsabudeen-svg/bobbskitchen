"""WebSocket broadcast helpers for server-push progress events.

Imports active_sessions from ws.py at call time to avoid circular imports.
All functions are fire-and-forget — they never raise; a disconnected client
simply causes the message to be silently dropped.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


async def broadcast(session_id: str, message: dict[str, Any]) -> None:
    """Send a JSON message to the WebSocket client for this session, if connected."""
    from app.api.ws import active_sessions  # late import — avoids circular dep

    ws = active_sessions.get(session_id)
    if ws is None:
        return
    try:
        await ws.send_json(message)
    except Exception:
        pass  # client disconnected mid-stream; ignore


async def send_generation_started(session_id: str, design_id: str, total: int) -> None:
    await broadcast(
        session_id,
        {
            "type": "generation_started",
            "design_id": design_id,
            "total_variants": total,
            "timestamp": _now(),
        },
    )


async def send_variant_ready(
    session_id: str,
    design_id: str,
    variant_number: int,
    variant_id: str,
    style: str,
    image_url: str | None,
    success: bool,
) -> None:
    await broadcast(
        session_id,
        {
            "type": "variant_ready",
            "design_id": design_id,
            "variant_number": variant_number,
            "variant_id": variant_id,
            "style": style,
            "image_url": image_url,
            "success": success,
            "timestamp": _now(),
        },
    )


async def send_generation_complete(
    session_id: str, design_id: str, variant_ids: list[str]
) -> None:
    await broadcast(
        session_id,
        {
            "type": "generation_complete",
            "design_id": design_id,
            "variant_ids": variant_ids,
            "timestamp": _now(),
        },
    )


async def send_refinement_started(
    session_id: str,
    design_id: str,
    parent_variant_id: str,
    refinement_type: str,
) -> None:
    await broadcast(
        session_id,
        {
            "type": "refinement_started",
            "design_id": design_id,
            "parent_variant_id": parent_variant_id,
            "refinement_type": refinement_type,
            "timestamp": _now(),
        },
    )


async def send_refinement_complete(
    session_id: str,
    design_id: str,
    new_variant_id: str,
    refinements_remaining: int,
) -> None:
    await broadcast(
        session_id,
        {
            "type": "refinement_complete",
            "design_id": design_id,
            "new_variant_id": new_variant_id,
            "refinements_remaining": refinements_remaining,
            "timestamp": _now(),
        },
    )
