"""WebSocket event flow and session recovery integration tests.

WebSocket Event Flow
--------------------
Connect a WS client, drive the HTTP pipeline (design → generate → select → refine),
and assert that the server pushed the correct sequence of broadcast events.

Expected event sequence:
  connect        → session_resumed
  POST /design   → (no WS event; strategy is persisted only)
  POST /generate → generation_started, variant_ready x4, generation_complete
  POST /select   → variant_selected
  POST /refine   → refinement_started, refinement_complete

Session Recovery
----------------
Connect, disconnect, reconnect to the same session_id.
Assert is_reconnect=False on first connect, is_reconnect=True on reconnect.

All tests use MockProvider + MockImageProvider — no external APIs.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.providers.mock import MockProvider
from app.services.image_gen import MockImageProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inject_providers(client: TestClient) -> MockProvider:
    llm = MockProvider()
    img = MockImageProvider()
    client.app.state.llm_provider = llm  # type: ignore[attr-defined]
    client.app.state.image_provider = img  # type: ignore[attr-defined]
    client.app.state.cache_dir = "cache/designs"  # type: ignore[attr-defined]
    return llm


_STORY_PAYLOAD = {
    "themes": ["backwaters", "fishing_heritage"],
    "emotions": ["nostalgia", "pride"],
    "keywords": ["fishing_boat", "coconut_palm"],
    "cultural_refs": ["Kerala backwaters"],
    "design_complexity": "medium",
    "intent": "DESIGN_REQUEST",
    "raw_customer_text": "I grew up fishing on the backwaters of Alappuzha",
}


def _create_session_with_design(client: TestClient) -> tuple[str, str, list[dict]]:
    """Create session, run design strategy. Returns (session_id, design_id, variants)."""
    sess = client.post("/api/v1/sessions").json()
    session_id: str = sess["session_id"]

    design = client.post(
        f"/api/v1/sessions/{session_id}/design",
        json={"story": _STORY_PAYLOAD},
    ).json()
    design_id: str = design["design_id"]

    gen = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id},
    ).json()
    variants: list[dict] = gen["variants"]
    return session_id, design_id, variants


def _collect_messages(ws, count: int) -> list[dict]:
    """Read exactly `count` JSON messages from the WebSocket."""
    return [ws.receive_json() for _ in range(count)]


def _messages_by_type(msgs: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for m in msgs:
        result.setdefault(m["type"], []).append(m)
    return result


# ---------------------------------------------------------------------------
# WS Event Flow — connect → generate
# ---------------------------------------------------------------------------


def test_ws_connect_sends_session_resumed(client: TestClient) -> None:
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    session_id = sess["session_id"]

    with client.websocket_connect(f"/ws/{session_id}") as ws:
        msg = ws.receive_json()

    assert msg["type"] == "session_resumed"
    assert msg["session_id"] == session_id
    assert msg["is_reconnect"] is False
    assert "state" in msg


def test_ws_generation_events_sequence(client: TestClient) -> None:
    """generation_started + 4×variant_ready + generation_complete arrive in order."""
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    session_id: str = sess["session_id"]

    design = client.post(
        f"/api/v1/sessions/{session_id}/design",
        json={"story": _STORY_PAYLOAD},
    ).json()
    design_id: str = design["design_id"]

    with client.websocket_connect(f"/ws/{session_id}") as ws:
        # consume session_resumed
        ws.receive_json()

        # trigger image generation while WS is connected
        client.post(
            f"/api/v1/sessions/{session_id}/generate",
            json={"design_id": design_id},
        )

        # generation_started + 4 variant_ready + generation_complete = 6 messages
        msgs = _collect_messages(ws, 6)

    by_type = _messages_by_type(msgs)

    # Exactly one generation_started
    assert len(by_type.get("generation_started", [])) == 1
    gs = by_type["generation_started"][0]
    assert gs["design_id"] == design_id
    assert gs["total_variants"] == 4

    # Exactly four variant_ready
    variant_ready = by_type.get("variant_ready", [])
    assert len(variant_ready) == 4
    styles = {m["style"] for m in variant_ready}
    assert styles == {"illustration", "geometric", "watercolor", "minimalist"}
    for m in variant_ready:
        assert m["design_id"] == design_id
        assert m["success"] is True
        assert "variant_id" in m
        assert "variant_number" in m

    # Exactly one generation_complete
    assert len(by_type.get("generation_complete", [])) == 1
    gc = by_type["generation_complete"][0]
    assert gc["design_id"] == design_id
    assert len(gc["variant_ids"]) == 4

    # Ordering: generation_started must be first, generation_complete must be last
    assert msgs[0]["type"] == "generation_started"
    assert msgs[-1]["type"] == "generation_complete"


def test_ws_generation_events_contain_timestamps(client: TestClient) -> None:
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    session_id: str = sess["session_id"]
    design = client.post(
        f"/api/v1/sessions/{session_id}/design",
        json={"story": _STORY_PAYLOAD},
    ).json()

    with client.websocket_connect(f"/ws/{session_id}") as ws:
        ws.receive_json()  # session_resumed
        client.post(
            f"/api/v1/sessions/{session_id}/generate",
            json={"design_id": design["design_id"]},
        )
        msgs = _collect_messages(ws, 6)

    for m in msgs:
        assert "timestamp" in m, f"message type '{m['type']}' missing timestamp"


def test_ws_no_events_when_not_connected(client: TestClient) -> None:
    """POST /generate without a connected WS must still succeed (broadcast is fire-and-forget)."""
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    session_id: str = sess["session_id"]
    design = client.post(
        f"/api/v1/sessions/{session_id}/design",
        json={"story": _STORY_PAYLOAD},
    ).json()

    # Intentionally NOT connecting WS
    gen_resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design["design_id"]},
    )
    assert gen_resp.status_code == 200
    assert len(gen_resp.json()["variants"]) == 4


# ---------------------------------------------------------------------------
# WS Event Flow — select and refine
# ---------------------------------------------------------------------------


def test_ws_variant_selected_event(client: TestClient) -> None:
    _inject_providers(client)
    session_id, design_id, variants = _create_session_with_design(client)
    variant_id: str = variants[0]["variant_id"]

    with client.websocket_connect(f"/ws/{session_id}") as ws:
        ws.receive_json()  # session_resumed

        client.post(
            f"/api/v1/designs/{design_id}/select",
            json={"variant_id": variant_id},
        )

        msg = ws.receive_json()

    assert msg["type"] == "variant_selected"
    assert msg["design_id"] == design_id
    assert msg["variant_id"] == variant_id


def test_ws_refinement_events(client: TestClient) -> None:
    """refinement_started and refinement_complete arrive after POST /refine."""
    _inject_providers(client)
    session_id, design_id, variants = _create_session_with_design(client)
    illustration = next(v for v in variants if v["style"] == "illustration")

    with client.websocket_connect(f"/ws/{session_id}") as ws:
        ws.receive_json()  # session_resumed

        client.post(
            f"/api/v1/designs/{design_id}/refine",
            json={"variant_id": illustration["variant_id"], "refinement_type": "more_cultural"},
        )

        started = ws.receive_json()
        complete = ws.receive_json()

    assert started["type"] == "refinement_started"
    assert started["design_id"] == design_id
    assert started["parent_variant_id"] == illustration["variant_id"]
    assert started["refinement_type"] == "more_cultural"

    assert complete["type"] == "refinement_complete"
    assert complete["design_id"] == design_id
    assert "new_variant_id" in complete
    assert isinstance(complete["refinements_remaining"], int)


def test_ws_full_generation_and_refine_sequence(client: TestClient) -> None:
    """All six event types arrive in one connected session."""
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    session_id: str = sess["session_id"]
    design = client.post(
        f"/api/v1/sessions/{session_id}/design",
        json={"story": _STORY_PAYLOAD},
    ).json()
    design_id: str = design["design_id"]

    with client.websocket_connect(f"/ws/{session_id}") as ws:
        ws.receive_json()  # session_resumed

        # generate → 6 events
        client.post(
            f"/api/v1/sessions/{session_id}/generate",
            json={"design_id": design_id},
        )
        gen_msgs = _collect_messages(ws, 6)

        # pick illustration variant
        gen_resp = client.get(f"/api/v1/designs/{design_id}/history").json()
        illustration = next(
            v for v in gen_resp["variants"]
            if v["style"] == "illustration" and v["is_initial_set"]
        )

        # select → 1 event
        client.post(
            f"/api/v1/designs/{design_id}/select",
            json={"variant_id": illustration["variant_id"]},
        )
        select_msg = ws.receive_json()

        # refine → 2 events
        client.post(
            f"/api/v1/designs/{design_id}/refine",
            json={"variant_id": illustration["variant_id"], "refinement_type": "more_minimal"},
        )
        refine_started = ws.receive_json()
        refine_complete = ws.receive_json()

    all_types = [m["type"] for m in gen_msgs] + [
        select_msg["type"],
        refine_started["type"],
        refine_complete["type"],
    ]

    assert all_types[0] == "generation_started"
    assert all_types.count("variant_ready") == 4
    assert "generation_complete" in all_types
    assert "variant_selected" in all_types
    assert "refinement_started" in all_types
    assert "refinement_complete" in all_types


# ---------------------------------------------------------------------------
# Session Recovery
# ---------------------------------------------------------------------------


def test_ws_first_connect_is_not_reconnect(client: TestClient) -> None:
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    session_id: str = sess["session_id"]

    with client.websocket_connect(f"/ws/{session_id}") as ws:
        msg = ws.receive_json()

    assert msg["type"] == "session_resumed"
    assert msg["is_reconnect"] is False


def test_ws_reconnect_sets_is_reconnect_true(client: TestClient) -> None:
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    session_id: str = sess["session_id"]

    # First connection
    with client.websocket_connect(f"/ws/{session_id}") as ws:
        first_msg = ws.receive_json()
    # ws disconnected — active_sessions entry removed

    # Reconnect
    with client.websocket_connect(f"/ws/{session_id}") as ws:
        second_msg = ws.receive_json()

    assert first_msg["is_reconnect"] is False
    assert second_msg["is_reconnect"] is True
    assert second_msg["type"] == "session_resumed"
    assert second_msg["session_id"] == session_id


def test_ws_reconnect_snapshot_structure(client: TestClient) -> None:
    """session_resumed always carries the expected top-level keys."""
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    session_id: str = sess["session_id"]

    with client.websocket_connect(f"/ws/{session_id}") as ws:
        msg = ws.receive_json()

    required_keys = {"type", "session_id", "state", "is_reconnect", "session"}
    assert required_keys.issubset(msg.keys()), (
        f"session_resumed missing keys: {required_keys - msg.keys()}"
    )


def test_ws_multiple_reconnects(client: TestClient) -> None:
    """Each reconnect after the first should have is_reconnect=True."""
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    session_id: str = sess["session_id"]

    for i in range(3):
        with client.websocket_connect(f"/ws/{session_id}") as ws:
            msg = ws.receive_json()
        assert msg["is_reconnect"] is (i > 0), f"connect {i}: wrong is_reconnect"


def test_ws_ping_pong(client: TestClient) -> None:
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    session_id: str = sess["session_id"]

    with client.websocket_connect(f"/ws/{session_id}") as ws:
        ws.receive_json()  # session_resumed
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()

    assert pong["type"] == "pong"
    assert "timestamp" in pong


def test_ws_unknown_session_still_accepts(client: TestClient) -> None:
    """WS accepts any session_id string; there is no pre-auth check."""
    _inject_providers(client)
    fake_id = str(uuid.uuid4())

    with client.websocket_connect(f"/ws/{fake_id}") as ws:
        msg = ws.receive_json()

    assert msg["type"] == "session_resumed"
    assert msg["session_id"] == fake_id


def test_ws_state_restored_after_generate_then_reconnect(client: TestClient) -> None:
    """After generating variants, reconnect returns session_resumed with real design state."""
    _inject_providers(client)
    session_id, design_id, variants = _create_session_with_design(client)

    # reconnect after full generate pipeline
    with client.websocket_connect(f"/ws/{session_id}") as ws:
        msg = ws.receive_json()

    assert msg["type"] == "session_resumed"
    assert msg["session_id"] == session_id
    assert msg["is_reconnect"] is True
    # Sprint 6: real DB state loaded — design and variants are present
    assert msg["latest_design"] is not None
    assert msg["latest_design"]["design_id"] == design_id
    assert len(msg["latest_design"]["variants"]) == 4
    # No recommendations generated yet
    assert msg["recommendations"] is None
    assert msg["order"] is None
    # State inferred from data: variants present → preview
    assert msg["state"] == "preview"
