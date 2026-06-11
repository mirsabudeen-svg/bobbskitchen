"""Integration tests for POST /api/v1/sessions/{session_id}/design.

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


def _make_story_payload() -> dict:
    return {
        "themes": ["backwaters", "fishing_heritage"],
        "emotions": ["nostalgia", "pride"],
        "keywords": ["fishing_boat", "coconut_palm"],
        "cultural_refs": ["Kerala backwaters"],
        "design_complexity": "medium",
        "intent": "DESIGN_REQUEST",
        "raw_customer_text": "I grew up fishing on the backwaters of Alappuzha",
    }


def _create_session_with_story(client: TestClient) -> tuple[str, MockProvider]:
    """Helper: create session, run story extraction, return session_id and provider."""
    sess = client.post("/api/v1/sessions").json()
    session_id = sess["session_id"]
    provider = _inject_mock_provider(client)
    client.post(
        f"/api/v1/sessions/{session_id}/story",
        json={"text": "I grew up fishing on the backwaters of Alappuzha"},
    )
    return session_id, provider


# ---------------------------------------------------------------------------
# Happy path — story provided inline
# ---------------------------------------------------------------------------


def test_design_strategy_with_inline_story(client: TestClient):
    sess = client.post("/api/v1/sessions").json()
    session_id = sess["session_id"]
    _inject_mock_provider(client)

    resp = client.post(
        f"/api/v1/sessions/{session_id}/design",
        json={"story": _make_story_payload()},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id
    assert uuid.UUID(body["design_id"])
    assert uuid.UUID(body["pipeline_run_id"])


def test_design_strategy_returns_four_variants(client: TestClient):
    sess = client.post("/api/v1/sessions").json()
    _inject_mock_provider(client)

    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/design",
        json={"story": _make_story_payload()},
    )
    assert len(resp.json()["strategy"]["variants"]) == 4


def test_design_strategy_all_variant_styles_present(client: TestClient):
    sess = client.post("/api/v1/sessions").json()
    _inject_mock_provider(client)

    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/design",
        json={"story": _make_story_payload()},
    )
    styles = {v["style"] for v in resp.json()["strategy"]["variants"]}
    assert styles == {"illustration", "geometric", "watercolor", "minimalist"}


def test_design_strategy_has_metadata(client: TestClient):
    sess = client.post("/api/v1/sessions").json()
    _inject_mock_provider(client)

    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/design",
        json={"story": _make_story_payload()},
    )
    meta = resp.json()["strategy"]["design_metadata"]
    assert "cultural_authenticity_score" in meta
    assert "print_feasibility" in meta
    assert "color_count" in meta
    assert "complexity" in meta
    assert "estimated_print_time_min" in meta


def test_design_strategy_returns_pipeline_run_id(client: TestClient):
    sess = client.post("/api/v1/sessions").json()
    _inject_mock_provider(client)

    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/design",
        json={"story": _make_story_payload()},
    )
    body = resp.json()
    run_id = uuid.UUID(body["pipeline_run_id"])
    assert str(run_id) == body["pipeline_run_id"]


def test_design_strategy_returns_product_suitability(client: TestClient):
    sess = client.post("/api/v1/sessions").json()
    _inject_mock_provider(client)

    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/design",
        json={"story": _make_story_payload()},
    )
    suitability = resp.json()["product_suitability"]
    assert isinstance(suitability, dict)
    assert "standard_tshirt" in suitability


def test_design_strategy_returns_primary_theme_and_emotion(client: TestClient):
    sess = client.post("/api/v1/sessions").json()
    _inject_mock_provider(client)

    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/design",
        json={"story": _make_story_payload()},
    )
    body = resp.json()
    assert body["primary_kerala_theme"] is not None
    assert body["primary_emotion"] is not None
    assert isinstance(body["key_symbols"], list)


# ---------------------------------------------------------------------------
# Happy path — story loaded from conversation_logs
# ---------------------------------------------------------------------------


def test_design_strategy_loads_story_from_conversation_logs(client: TestClient):
    session_id, _ = _create_session_with_story(client)

    resp = client.post(
        f"/api/v1/sessions/{session_id}/design",
        json={},  # no inline story — should load from DB
    )
    assert resp.status_code == 200
    assert uuid.UUID(resp.json()["design_id"])


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_design_404_for_unknown_session(client: TestClient):
    _inject_mock_provider(client)
    resp = client.post(
        f"/api/v1/sessions/{uuid.uuid4()}/design",
        json={"story": _make_story_payload()},
    )
    assert resp.status_code == 404


def test_design_422_for_invalid_session_id(client: TestClient):
    _inject_mock_provider(client)
    resp = client.post(
        "/api/v1/sessions/not-a-uuid/design",
        json={"story": _make_story_payload()},
    )
    assert resp.status_code == 422


def test_design_503_when_no_provider(client: TestClient):
    client.app.state.llm_provider = None  # type: ignore[attr-defined]
    sess = client.post("/api/v1/sessions").json()
    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/design",
        json={"story": _make_story_payload()},
    )
    assert resp.status_code == 503


def test_design_422_no_story_and_no_conversation_history(client: TestClient):
    _inject_mock_provider(client)
    sess = client.post("/api/v1/sessions").json()
    # Session exists but has no conversation_logs -> no story to load
    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/design",
        json={},  # no inline story, no history
    )
    assert resp.status_code == 422
