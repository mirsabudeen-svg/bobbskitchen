"""Integration tests for Sprint 4 design endpoints.

POST /api/v1/designs/{id}/select
POST /api/v1/designs/{id}/refine
GET  /api/v1/designs/{id}/history
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.providers.mock import MockProvider
from app.services.image_gen import MockImageProvider
from app.services.refinement import MAX_REFINEMENTS


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


def _setup_generated_design(client: TestClient) -> tuple[str, str, list[str]]:
    """Create session → design → generate. Returns (session_id, design_id, variant_ids)."""
    sess = client.post("/api/v1/sessions").json()
    session_id = sess["session_id"]
    _inject_providers(client)

    design_resp = client.post(
        f"/api/v1/sessions/{session_id}/design",
        json={"story": _make_story_payload()},
    )
    assert design_resp.status_code == 200
    design_id = design_resp.json()["design_id"]

    gen_resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id},
    )
    assert gen_resp.status_code == 200
    variant_ids = [v["variant_id"] for v in gen_resp.json()["variants"]]
    return session_id, design_id, variant_ids


# ---------------------------------------------------------------------------
# SELECT tests
# ---------------------------------------------------------------------------


def test_select_variant_returns_200(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    resp = client.post(
        f"/api/v1/designs/{design_id}/select",
        json={"variant_id": variant_ids[0]},
    )
    assert resp.status_code == 200


def test_select_variant_locks_design(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    resp = client.post(
        f"/api/v1/designs/{design_id}/select",
        json={"variant_id": variant_ids[1]},
    )
    body = resp.json()
    assert body["design_locked"] is True
    assert body["selected_variant_id"] == variant_ids[1]


def test_select_variant_is_idempotent(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    vid = variant_ids[2]
    r1 = client.post(f"/api/v1/designs/{design_id}/select", json={"variant_id": vid})
    r2 = client.post(f"/api/v1/designs/{design_id}/select", json={"variant_id": vid})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["selected_variant_id"] == r2.json()["selected_variant_id"]


def test_select_variant_404_unknown_design(client: TestClient):
    _inject_providers(client)
    resp = client.post(
        f"/api/v1/designs/{uuid.uuid4()}/select",
        json={"variant_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


def test_select_variant_404_variant_not_in_design(client: TestClient):
    _, design_id, _ = _setup_generated_design(client)
    resp = client.post(
        f"/api/v1/designs/{design_id}/select",
        json={"variant_id": str(uuid.uuid4())},  # unknown variant
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# REFINE tests
# ---------------------------------------------------------------------------


def test_refine_returns_200(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    resp = client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": variant_ids[0], "refinement_type": "more_minimal"},
    )
    assert resp.status_code == 200


def test_refine_returns_new_variant_id(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    resp = client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": variant_ids[0], "refinement_type": "more_cultural"},
    )
    body = resp.json()
    assert uuid.UUID(body["new_variant_id"])
    assert body["new_variant_id"] not in variant_ids


def test_refine_variant_number_is_5_or_higher(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    resp = client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": variant_ids[0], "refinement_type": "more_modern"},
    )
    assert resp.json()["variant_number"] >= 5


def test_refine_reports_refinements_used_and_remaining(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    resp = client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": variant_ids[0], "refinement_type": "more_premium"},
    )
    body = resp.json()
    assert body["refinements_used"] == 1
    assert body["refinements_remaining"] == MAX_REFINEMENTS - 1


def test_refine_preserves_parent_variant_id(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    parent_vid = variant_ids[0]
    resp = client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": parent_vid, "refinement_type": "different_colours"},
    )
    assert resp.json()["parent_variant_id"] == parent_vid


def test_refine_limit_enforced(client: TestClient):
    """After MAX_REFINEMENTS refinements, a 422 is returned."""
    _, design_id, variant_ids = _setup_generated_design(client)
    parent_vid = variant_ids[0]

    # Exhaust the limit
    for _ in range(MAX_REFINEMENTS):
        r = client.post(
            f"/api/v1/designs/{design_id}/refine",
            json={"variant_id": parent_vid, "refinement_type": "different_layout"},
        )
        assert r.status_code == 200

    # Next refinement must be rejected
    over = client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": parent_vid, "refinement_type": "more_minimal"},
    )
    assert over.status_code == 422
    assert "limit" in over.json()["detail"].lower()


def test_refine_404_unknown_design(client: TestClient):
    _inject_providers(client)
    resp = client.post(
        f"/api/v1/designs/{uuid.uuid4()}/refine",
        json={"variant_id": str(uuid.uuid4()), "refinement_type": "more_minimal"},
    )
    assert resp.status_code == 404


def test_refine_404_variant_not_in_design(client: TestClient):
    _, design_id, _ = _setup_generated_design(client)
    resp = client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": str(uuid.uuid4()), "refinement_type": "more_minimal"},
    )
    assert resp.status_code == 404


def test_refine_with_seed_passes_through(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    resp = client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": variant_ids[0], "refinement_type": "more_minimal", "seed": 42},
    )
    assert resp.json()["generation_seed"] == 42


# ---------------------------------------------------------------------------
# HISTORY tests
# ---------------------------------------------------------------------------


def test_history_returns_initial_variants(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    resp = client.get(f"/api/v1/designs/{design_id}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_variants"] == 4


def test_history_includes_refined_variants(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": variant_ids[0], "refinement_type": "more_minimal"},
    )
    resp = client.get(f"/api/v1/designs/{design_id}/history")
    assert resp.json()["total_variants"] == 5


def test_history_has_parent_variant_id_for_refined(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    parent_vid = variant_ids[1]
    refine_resp = client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": parent_vid, "refinement_type": "more_cultural"},
    )
    new_vid = refine_resp.json()["new_variant_id"]

    history = client.get(f"/api/v1/designs/{design_id}/history").json()["variants"]
    refined = next(v for v in history if v["variant_id"] == new_vid)
    assert refined["parent_variant_id"] == parent_vid
    assert refined["is_refined"] is True
    assert refined["is_initial_set"] is False
    assert refined["refinement_type"] == "more_cultural"


def test_history_initial_variants_have_no_parent(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    history = client.get(f"/api/v1/designs/{design_id}/history").json()["variants"]
    for v in history:
        assert v["is_initial_set"] is True
        assert v["parent_variant_id"] is None


def test_history_ordered_by_variant_number(client: TestClient):
    _, design_id, variant_ids = _setup_generated_design(client)
    client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": variant_ids[2], "refinement_type": "more_premium"},
    )
    history = client.get(f"/api/v1/designs/{design_id}/history").json()["variants"]
    numbers = [v["variant_number"] for v in history]
    assert numbers == sorted(numbers)


def test_history_404_unknown_design(client: TestClient):
    resp = client.get(f"/api/v1/designs/{uuid.uuid4()}/history")
    assert resp.status_code == 404
