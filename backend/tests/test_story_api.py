"""Integration tests for POST /api/v1/sessions/{session_id}/story.

Uses the real DB (via app.state fixture) and MockProvider (no Anthropic calls).
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.providers.mock import MockProvider


def _inject_mock_provider(client: TestClient, responses=None) -> MockProvider:
    provider = MockProvider(responses=responses)
    client.app.state.llm_provider = provider  # type: ignore[attr-defined]
    return provider


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_story_extraction_creates_session_and_extracts(client: TestClient):
    # Create session first
    sess = client.post("/api/v1/sessions")
    assert sess.status_code == 201
    session_id = sess.json()["session_id"]

    _inject_mock_provider(client)

    resp = client.post(
        f"/api/v1/sessions/{session_id}/story",
        json={"text": "I grew up fishing by the Vembanad Lake"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["session_id"] == session_id
    assert body["turn_number"] == 1
    assert body["needs_clarification"] is False
    assert "backwaters" in body["story"]["themes"] or "fishing_heritage" in body["story"]["themes"]
    assert uuid.UUID(body["pipeline_run_id"])  # valid UUID


def test_story_extraction_returns_pipeline_run_id(client: TestClient):
    sess = client.post("/api/v1/sessions").json()
    _inject_mock_provider(client)

    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/story",
        json={"text": "backwaters of Alleppey"},
    )
    body = resp.json()
    run_id = uuid.UUID(body["pipeline_run_id"])  # must be valid UUID
    assert str(run_id) == body["pipeline_run_id"]


def test_story_extraction_increments_turn_number(client: TestClient):
    sess = client.post("/api/v1/sessions").json()
    session_id = sess["session_id"]
    _inject_mock_provider(client)

    r1 = client.post(
        f"/api/v1/sessions/{session_id}/story",
        json={"text": "first input"},
    )
    r2 = client.post(
        f"/api/v1/sessions/{session_id}/story",
        json={"text": "second input"},
    )
    assert r1.json()["turn_number"] == 1
    assert r2.json()["turn_number"] == 2


def test_story_extraction_passes_history_on_second_turn(client: TestClient):
    """On the second call, the provider should receive 3 messages (user+assistant+user)."""
    sess = client.post("/api/v1/sessions").json()
    session_id = sess["session_id"]

    # First turn — mock returns needs_clarification=False but agent_text_reply set via canned
    clarify_response = {
        "themes": [],
        "emotions": [],
        "symbols": [],
        "cultural_elements": [],
        "design_complexity": "simple",
        "intent": "DESIGN_REQUEST",
        "needs_clarification": True,
        "clarification_question": "Which district of Kerala?",
        "raw_customer_text": "home",
        "confidence": 0.5,
        "clarity_score": 0.4,
    }
    provider = _inject_mock_provider(client, responses={"submit_story": clarify_response})
    client.post(f"/api/v1/sessions/{session_id}/story", json={"text": "home"})

    # Second turn — swap to default response
    provider._responses["submit_story"] = {
        "themes": ["backwaters"],
        "emotions": ["nostalgia"],
        "symbols": ["boat"],
        "cultural_elements": [],
        "design_complexity": "medium",
        "intent": "DESIGN_REQUEST",
        "needs_clarification": False,
        "clarification_question": None,
        "raw_customer_text": "Alappuzha",
        "confidence": 0.9,
        "clarity_score": 0.85,
    }
    client.post(f"/api/v1/sessions/{session_id}/story", json={"text": "Alappuzha"})

    # Second call should have 3 messages in history
    second_call = provider.calls[1]
    assert len(second_call["messages"]) == 3


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_story_extraction_404_for_unknown_session(client: TestClient):
    _inject_mock_provider(client)
    resp = client.post(
        f"/api/v1/sessions/{uuid.uuid4()}/story",
        json={"text": "test"},
    )
    assert resp.status_code == 404


def test_story_extraction_422_for_invalid_session_id(client: TestClient):
    _inject_mock_provider(client)
    resp = client.post(
        "/api/v1/sessions/not-a-uuid/story",
        json={"text": "test"},
    )
    assert resp.status_code == 422


def test_story_extraction_503_when_no_provider(client: TestClient):
    client.app.state.llm_provider = None  # type: ignore[attr-defined]
    sess = client.post("/api/v1/sessions").json()
    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/story",
        json={"text": "test"},
    )
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Session GET endpoint (Sprint 1)
# ---------------------------------------------------------------------------

def test_get_session_returns_state(client: TestClient):
    sess = client.post("/api/v1/sessions").json()
    resp = client.get(f"/api/v1/sessions/{sess['session_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "greeting"
    assert body["ws_path"] == f"/ws/{sess['session_id']}"


def test_get_session_404_for_unknown(client: TestClient):
    resp = client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert resp.status_code == 404
