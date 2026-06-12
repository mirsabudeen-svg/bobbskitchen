"""Sprint 6.2 acceptance tests — critical data integrity fixes.

1. Session contamination: POST /sessions/{id}/abandon marks the row abandoned;
   a subsequent session is a separate DB row.
2. Null variant guard: selecting a fallback variant (image_url=None) -> 422.
3. Total generation failure: all variants failing -> HTTP 503 (uses a
   failing image provider injected via app.state — MockImageProvider itself
   has no failure mode, so we define one here).

Uses MockProvider + a mock image provider exclusively — no external APIs.
DB assertions run in a fresh asyncio loop with a dedicated engine (same
pattern as test_e2e_story_to_recommendation.py).
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.db.base import create_engine, create_session_factory
from app.models.db import DesignVariantRow
from app.models.db import Session as SessionRow
from app.providers.mock import MockProvider
from app.services.image_gen import (
    GenerationParams,
    GenerationResult,
    MockImageProvider,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CUSTOMER_TEXT = "I grew up fishing on the backwaters of Alappuzha with my grandfather"

_STORY_PAYLOAD = {
    "themes": ["backwaters", "fishing_heritage"],
    "emotions": ["nostalgia", "pride"],
    "keywords": ["fishing_boat", "coconut_palm"],
    "cultural_refs": ["Kerala backwaters"],
    "design_complexity": "medium",
    "intent": "DESIGN_REQUEST",
    "raw_customer_text": _CUSTOMER_TEXT,
}


class FailingImageProvider:
    """Image provider where every generation fails — simulates total fal.ai outage."""

    provider_name = "mock-failing"

    async def generate(
        self,
        params: GenerationParams,
        *,
        output_dir: Path,
        variant_number: int,
        session_id: uuid.UUID,
    ) -> GenerationResult:
        return GenerationResult(
            success=False,
            image_url=None,
            image_path=None,
            provider_request_id=None,
            generation_seed=None,
            generation_time_ms=0,
            model_used="mock-failing",
            provider_name=self.provider_name,
            error="simulated provider outage",
        )


def _inject_providers(client: TestClient, image_provider: Any | None = None) -> None:
    client.app.state.llm_provider = MockProvider()  # type: ignore[attr-defined]
    client.app.state.image_provider = image_provider or MockImageProvider()  # type: ignore[attr-defined]
    client.app.state.cache_dir = "cache/designs"  # type: ignore[attr-defined]


def _run_async(coro: Any) -> Any:
    """Run a coroutine with a dedicated engine/loop (see module docstring)."""
    return asyncio.run(coro)


async def _with_fresh_db(fn: Any) -> Any:
    settings = get_settings()
    engine = create_engine(settings)
    factory: async_sessionmaker = create_session_factory(engine)
    try:
        async with factory() as db:
            return await fn(db)
    finally:
        await engine.dispose()


def _create_design_with_variants(client: TestClient, session_id: str) -> dict:
    """Run story -> design -> generate via mocks; return generate response body."""
    story_resp = client.post(
        f"/api/v1/sessions/{session_id}/story", json={"text": _CUSTOMER_TEXT}
    )
    assert story_resp.status_code == 200, story_resp.text

    design_resp = client.post(
        f"/api/v1/sessions/{session_id}/design", json={"story": _STORY_PAYLOAD}
    )
    assert design_resp.status_code == 200, design_resp.text
    design_id = design_resp.json()["design_id"]

    gen_resp = client.post(
        f"/api/v1/sessions/{session_id}/generate", json={"design_id": design_id}
    )
    assert gen_resp.status_code == 200, gen_resp.text
    return gen_resp.json()


# ---------------------------------------------------------------------------
# Test 1 — Session contamination / abandon endpoint
# ---------------------------------------------------------------------------


def test_abandon_session_isolates_customers(client: TestClient) -> None:
    _inject_providers(client)

    # Customer A
    resp_a = client.post("/api/v1/sessions")
    assert resp_a.status_code == 201, resp_a.text
    session_a = resp_a.json()["session_id"]

    # Idle timeout fires -> frontend abandons the session
    abandon_resp = client.post(f"/api/v1/sessions/{session_a}/abandon")
    assert abandon_resp.status_code == 200, abandon_resp.text
    assert abandon_resp.json() == {"abandoned": True, "session_id": session_a}

    # Customer B gets a brand-new session
    resp_b = client.post("/api/v1/sessions")
    assert resp_b.status_code == 201, resp_b.text
    session_b = resp_b.json()["session_id"]
    assert session_a != session_b

    async def _assert(db: Any) -> None:
        rows = (
            await db.execute(
                select(SessionRow).where(
                    SessionRow.id.in_([uuid.UUID(session_a), uuid.UUID(session_b)])
                )
            )
        ).scalars().all()
        by_id = {str(r.id): r for r in rows}
        assert len(by_id) == 2, "Sessions A and B must be separate DB rows"
        row_a = by_id[session_a]
        assert row_a.abandoned is True
        assert row_a.completed is False
        assert row_a.current_state == "idle"
        row_b = by_id[session_b]
        assert row_b.abandoned is False

    _run_async(_with_fresh_db(_assert))


def test_abandon_unknown_session_404(client: TestClient) -> None:
    resp = client.post(f"/api/v1/sessions/{uuid.uuid4()}/abandon")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 2 — Null variant guard on /select
# ---------------------------------------------------------------------------


def test_select_null_image_variant_rejected(client: TestClient) -> None:
    _inject_providers(client)

    sess_resp = client.post("/api/v1/sessions")
    assert sess_resp.status_code == 201
    session_id = sess_resp.json()["session_id"]

    gen_body = _create_design_with_variants(client, session_id)
    design_id = gen_body["design_id"]

    # Insert a failed/fallback variant row directly (image_url=None)
    async def _insert(db: Any) -> str:
        row = DesignVariantRow(
            id=uuid.uuid4(),
            design_id=uuid.UUID(design_id),
            variant_number=99,
            is_initial_set=True,
            prompt_used="failed variant",
            style="illustration",
            image_url=None,
            is_fallback=True,
        )
        db.add(row)
        await db.commit()
        return str(row.id)

    fallback_variant_id = _run_async(_with_fresh_db(_insert))

    resp = client.post(
        f"/api/v1/designs/{design_id}/select",
        json={"variant_id": fallback_variant_id},
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "variant_not_printable"
    assert detail["suggested_action"] == "regenerate"

    # A healthy variant is still selectable
    good = next(v for v in gen_body["variants"] if v["image_url"])
    ok = client.post(
        f"/api/v1/designs/{design_id}/select",
        json={"variant_id": good["variant_id"]},
    )
    assert ok.status_code == 200, ok.text


# ---------------------------------------------------------------------------
# Test 3 — Total generation failure returns 503
# ---------------------------------------------------------------------------


def test_total_generation_failure_returns_503(client: TestClient) -> None:
    # MockImageProvider has no built-in failure mode, so inject a provider
    # whose every call fails (simulating a total fal.ai outage).
    _inject_providers(client, image_provider=FailingImageProvider())

    sess_resp = client.post("/api/v1/sessions")
    assert sess_resp.status_code == 201
    session_id = sess_resp.json()["session_id"]

    story_resp = client.post(
        f"/api/v1/sessions/{session_id}/story", json={"text": _CUSTOMER_TEXT}
    )
    assert story_resp.status_code == 200, story_resp.text

    design_resp = client.post(
        f"/api/v1/sessions/{session_id}/design", json={"story": _STORY_PAYLOAD}
    )
    assert design_resp.status_code == 200, design_resp.text
    design_id = design_resp.json()["design_id"]

    gen_resp = client.post(
        f"/api/v1/sessions/{session_id}/generate", json={"design_id": design_id}
    )
    assert gen_resp.status_code == 503, gen_resp.text
    detail = gen_resp.json()["detail"]
    assert detail["error"] == "image_generation_failed"
    assert detail["successful_count"] == 0
    assert detail["failed_count"] > 0
