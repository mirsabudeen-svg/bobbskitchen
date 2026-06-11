"""Integration tests for POST /api/v1/sessions/{session_id}/generate.

Uses the real DB (via app.state fixture), MockProvider for LLM, and
MockImageProvider for image generation.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.providers.mock import MockProvider
from app.services.image_gen import MockImageProvider


def _inject_providers(client: TestClient) -> tuple[MockProvider, MockImageProvider]:
    llm = MockProvider()
    img = MockImageProvider()
    client.app.state.llm_provider = llm  # type: ignore[attr-defined]
    client.app.state.image_provider = img  # type: ignore[attr-defined]
    client.app.state.cache_dir = "cache/designs"  # type: ignore[attr-defined]
    return llm, img


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


def _setup_session_with_design(client: TestClient) -> tuple[str, str]:
    """Create session → design strategy. Returns (session_id, design_id)."""
    sess = client.post("/api/v1/sessions").json()
    session_id = sess["session_id"]
    _inject_providers(client)

    design_resp = client.post(
        f"/api/v1/sessions/{session_id}/design",
        json={"story": _make_story_payload()},
    )
    assert design_resp.status_code == 200
    design_id = design_resp.json()["design_id"]
    return session_id, design_id


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_generate_returns_200(client: TestClient):
    session_id, design_id = _setup_session_with_design(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id},
    )
    assert resp.status_code == 200


def test_generate_returns_four_variants(client: TestClient):
    session_id, design_id = _setup_session_with_design(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id},
    )
    variants = resp.json()["variants"]
    assert len(variants) == 4


def test_generate_all_variants_succeed(client: TestClient):
    session_id, design_id = _setup_session_with_design(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id},
    )
    assert all(v["success"] for v in resp.json()["variants"])


def test_generate_variant_numbers_1_to_4(client: TestClient):
    session_id, design_id = _setup_session_with_design(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id},
    )
    numbers = {v["variant_number"] for v in resp.json()["variants"]}
    assert numbers == {1, 2, 3, 4}


def test_generate_all_styles_present(client: TestClient):
    session_id, design_id = _setup_session_with_design(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id},
    )
    styles = {v["style"] for v in resp.json()["variants"]}
    assert styles == {"illustration", "geometric", "watercolor", "minimalist"}


def test_generate_returns_design_id_and_pipeline_run_id(client: TestClient):
    session_id, design_id = _setup_session_with_design(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id},
    )
    body = resp.json()
    assert uuid.UUID(body["design_id"])
    assert uuid.UUID(body["pipeline_run_id"])


def test_generate_variants_have_required_fields(client: TestClient):
    session_id, design_id = _setup_session_with_design(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id},
    )
    for v in resp.json()["variants"]:
        assert uuid.UUID(v["variant_id"])
        assert v["provider_name"] == "mock"
        assert v["generation_seed"] is not None
        assert v["provider_request_id"] is not None


def test_generate_without_design_id_uses_latest(client: TestClient):
    """Omitting design_id should auto-select the latest design for the session."""
    session_id, _ = _setup_session_with_design(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={},
    )
    assert resp.status_code == 200
    assert len(resp.json()["variants"]) == 4


def test_generate_with_seeds_passes_through(client: TestClient):
    session_id, design_id = _setup_session_with_design(client)
    seeds = [111, 222, 333, 444]
    resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id, "seeds": seeds},
    )
    result_seeds = sorted(
        [v["generation_seed"] for v in resp.json()["variants"]]
    )
    assert result_seeds == sorted(seeds)


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_generate_404_unknown_session(client: TestClient):
    _inject_providers(client)
    resp = client.post(
        f"/api/v1/sessions/{uuid.uuid4()}/generate",
        json={},
    )
    assert resp.status_code == 404


def test_generate_422_invalid_session_id(client: TestClient):
    _inject_providers(client)
    resp = client.post("/api/v1/sessions/not-a-uuid/generate", json={})
    assert resp.status_code == 422


def test_generate_422_no_design_for_session(client: TestClient):
    _inject_providers(client)
    sess = client.post("/api/v1/sessions").json()
    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/generate",
        json={},
    )
    assert resp.status_code == 422


def test_generate_503_no_image_provider(client: TestClient):
    client.app.state.llm_provider = MockProvider()  # type: ignore[attr-defined]
    client.app.state.image_provider = None  # type: ignore[attr-defined]
    sess = client.post("/api/v1/sessions").json()
    resp = client.post(
        f"/api/v1/sessions/{sess['session_id']}/generate",
        json={},
    )
    assert resp.status_code == 503
