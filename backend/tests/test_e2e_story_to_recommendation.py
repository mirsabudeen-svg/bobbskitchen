"""End-to-end integration test: story → recommendation.

Covers the full customer pipeline in a single test function:
  1. Create Session
  2. Submit Story   (ConversationAgent / submit_story)
  3. Generate Design Strategy  (DesignAgent / submit_design_strategy)
  4. Generate 4 Variants  (ImageGenerationService / MockImageProvider)
  5. Select Variant
  6. Refine Variant  (RefinementType)
  7. Generate Product Recommendations  (ProductAgent / submit_recommendations)

Assertions verified across the pipeline:
  - pipeline_run_id preserved through design → generate → recommend
  - prompt_version stored per agent_log row
  - agent_logs rows created for every agent call
  - design_strategy_json persisted before image generation
  - 4 initial variants persisted with correct style ordering
  - variant lineage (parent_variant_id, is_refined) preserved after refinement
  - recommendations_json persisted; GET /recommendations returns the same data

Uses MockProvider + MockImageProvider exclusively — no external APIs.

NOTE: DB-level assertions (agent_logs, design row) run inside asyncio.run() with a
fresh engine so they don't share the session-scoped asyncpg pool and never
bind pool connections to a different event loop than the TestClient/anyio tests.
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.db.base import create_engine, create_session_factory
from app.models.db import AgentLog, Design, DesignVariantRow
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


def _run_db_assertions(design_id: str, session_id: str, design_pipeline_run_id: str) -> None:
    """Run all DB-level assertions in a fresh asyncio event loop with a dedicated engine.

    Keeps our async SQLAlchemy queries in their own loop so they never touch the
    session-scoped asyncpg pool that the TestClient/anyio tests share.
    """

    async def _assert() -> None:
        settings = get_settings()
        engine = create_engine(settings)
        factory: async_sessionmaker = create_session_factory(engine)

        try:
            async with factory() as db:
                # ---- Design row ----
                design_result = await db.execute(
                    select(Design).where(Design.id == uuid.UUID(design_id))
                )
                design = design_result.scalar_one()
                assert design.design_strategy_json is not None, (
                    "design_strategy_json must be persisted before image generation"
                )
                assert len(design.design_strategy_json["variants"]) == 4
                assert design.story_json is not None
                assert design.pipeline_run_id == uuid.UUID(design_pipeline_run_id), (
                    "pipeline_run_id must be preserved from /design through /generate"
                )

                # ---- Variant rows ----
                variants_result = await db.execute(
                    select(DesignVariantRow)
                    .where(DesignVariantRow.design_id == uuid.UUID(design_id))
                    .order_by(DesignVariantRow.variant_number)
                )
                all_variants = list(variants_result.scalars().all())

                initial = [v for v in all_variants if v.is_initial_set]
                assert len(initial) == 4, "exactly 4 initial variants must be persisted"
                assert {v.style for v in initial} == {
                    "illustration", "geometric", "watercolor", "minimalist"
                }
                for v in initial:
                    assert v.design_id == uuid.UUID(design_id)
                    assert not v.is_refined
                    assert v.parent_variant_id is None

                refined = [v for v in all_variants if v.is_refined]
                assert len(refined) == 1, "exactly 1 refined variant must be persisted"
                ref = refined[0]
                assert ref.is_initial_set is False
                assert ref.parent_variant_id is not None
                assert ref.refinement_type == "more_cultural"

                # ---- Recommendations ----
                assert design.recommendations_json is not None, "recommendations must be persisted"
                assert len(design.recommendations_json) == 3
                assert design.recommendations_generated_at is not None
                assert design.recommendations_model is not None

                # ---- Agent logs ----
                logs_result = await db.execute(
                    select(AgentLog)
                    .where(AgentLog.session_id == uuid.UUID(session_id))
                    .order_by(AgentLog.created_at)
                )
                logs = list(logs_result.scalars().all())
                agent_names = [log.agent_name for log in logs]
                assert "conversation" in agent_names, "conversation agent log missing"
                assert "design" in agent_names, "design agent log missing"
                assert "product" in agent_names, "product agent log missing"

                for log in logs:
                    assert log.prompt_version is not None, (
                        f"agent_log for '{log.agent_name}' missing prompt_version"
                    )
                    assert len(log.prompt_version) == 40, (
                        f"agent_log for '{log.agent_name}' has malformed prompt_version"
                    )
                    assert log.success is True
                    assert log.tokens_input is not None and log.tokens_input >= 0
                    assert log.tokens_output is not None and log.tokens_output >= 0

                design_log = next(log for log in logs if log.agent_name == "design")
                assert str(design_log.pipeline_run_id) == design_pipeline_run_id, (
                    "design agent_log.pipeline_run_id must match /design response"
                )

                product_log = next(log for log in logs if log.agent_name == "product")
                assert product_log.pipeline_run_id is not None

                conv_log = next(log for log in logs if log.agent_name == "conversation")
                assert str(conv_log.session_id) == session_id

        finally:
            await engine.dispose()

    asyncio.run(_assert())


# ---------------------------------------------------------------------------
# End-to-end test
# ---------------------------------------------------------------------------


def test_e2e_story_to_recommendation(
    client: TestClient,
    db_session_factory: async_sessionmaker,  # noqa: ARG001 — kept for fixture wiring
) -> None:
    """Full pipeline: session → story → design → generate → select → refine → recommend."""

    llm = _inject_providers(client)

    # ------------------------------------------------------------------
    # Step 1 — Create Session
    # ------------------------------------------------------------------
    sess_resp = client.post("/api/v1/sessions")
    assert sess_resp.status_code == 201, sess_resp.text
    session_id: str = sess_resp.json()["session_id"]
    assert uuid.UUID(session_id)

    # ------------------------------------------------------------------
    # Step 2 — Submit Story (ConversationAgent)
    # ------------------------------------------------------------------
    story_resp = client.post(
        f"/api/v1/sessions/{session_id}/story",
        json={"text": _CUSTOMER_TEXT},
    )
    assert story_resp.status_code == 200, story_resp.text
    story_body = story_resp.json()

    story_pipeline_run_id: str = story_body["pipeline_run_id"]
    assert uuid.UUID(story_pipeline_run_id)
    assert story_body["story"]["intent"] == "DESIGN_REQUEST"
    assert not story_body["needs_clarification"]

    # ------------------------------------------------------------------
    # Step 3 — Generate Design Strategy (DesignAgent)
    # ------------------------------------------------------------------
    design_resp = client.post(
        f"/api/v1/sessions/{session_id}/design",
        json={"story": _STORY_PAYLOAD},
    )
    assert design_resp.status_code == 200, design_resp.text
    design_body = design_resp.json()

    design_id: str = design_body["design_id"]
    design_pipeline_run_id: str = design_body["pipeline_run_id"]
    assert uuid.UUID(design_id)
    assert uuid.UUID(design_pipeline_run_id)
    assert len(design_body["strategy"]["variants"]) == 4

    # ------------------------------------------------------------------
    # Step 4 — Generate 4 Variants (MockImageProvider)
    # ------------------------------------------------------------------
    gen_resp = client.post(
        f"/api/v1/sessions/{session_id}/generate",
        json={"design_id": design_id},
    )
    assert gen_resp.status_code == 200, gen_resp.text
    gen_body = gen_resp.json()

    gen_pipeline_run_id: str = gen_body["pipeline_run_id"]
    assert gen_pipeline_run_id == design_pipeline_run_id, (
        "pipeline_run_id must be preserved from /design through /generate"
    )
    assert len(gen_body["variants"]) == 4

    # All 4 styles present in response
    styles = {v["style"] for v in gen_body["variants"]}
    assert styles == {"illustration", "geometric", "watercolor", "minimalist"}

    # Pick illustration variant for selection + refinement
    variant_1 = next(v for v in gen_body["variants"] if v["style"] == "illustration")
    variant_1_id: str = variant_1["variant_id"]

    # ------------------------------------------------------------------
    # Step 5 — Select Variant
    # ------------------------------------------------------------------
    select_resp = client.post(
        f"/api/v1/designs/{design_id}/select",
        json={"variant_id": variant_1_id},
    )
    assert select_resp.status_code == 200, select_resp.text
    select_body = select_resp.json()
    assert select_body["design_locked"] is True
    assert select_body["selected_variant_id"] == variant_1_id

    # ------------------------------------------------------------------
    # Step 6 — Refine Variant (more_cultural)
    # ------------------------------------------------------------------
    refine_resp = client.post(
        f"/api/v1/designs/{design_id}/refine",
        json={"variant_id": variant_1_id, "refinement_type": "more_cultural"},
    )
    assert refine_resp.status_code == 200, refine_resp.text
    refine_body = refine_resp.json()

    refined_variant_id: str = refine_body["new_variant_id"]
    assert uuid.UUID(refined_variant_id)
    assert refine_body["parent_variant_id"] == variant_1_id
    assert refine_body["refinement_type"] == "more_cultural"
    assert refine_body["refinements_used"] == 1
    assert refine_body["refinements_remaining"] == 2

    # Verify lineage via history API
    history_resp = client.get(f"/api/v1/designs/{design_id}/history")
    assert history_resp.status_code == 200, history_resp.text
    history = history_resp.json()
    assert history["total_variants"] == 5  # 4 initial + 1 refined

    refined_in_history = next(
        v for v in history["variants"] if v["variant_id"] == refined_variant_id
    )
    assert refined_in_history["is_refined"] is True
    assert refined_in_history["is_initial_set"] is False
    assert refined_in_history["parent_variant_id"] == variant_1_id
    assert refined_in_history["refinement_type"] == "more_cultural"

    initial_in_history = [v for v in history["variants"] if v["is_initial_set"]]
    assert len(initial_in_history) == 4

    # ------------------------------------------------------------------
    # Step 7 — Generate Product Recommendations (ProductAgent)
    # ------------------------------------------------------------------
    rec_resp = client.post(f"/api/v1/designs/{design_id}/recommend")
    assert rec_resp.status_code == 200, rec_resp.text
    rec_body = rec_resp.json()

    assert uuid.UUID(rec_body["pipeline_run_id"])
    recs = rec_body["recommendations"]
    assert len(recs) == 3
    assert [r["rank"] for r in recs] == [1, 2, 3]

    for r in recs:
        assert r["score"] > 0
        sb = r["score_breakdown"]
        assert 0.0 <= sb["design_fit"] <= 1.0
        assert 0.0 <= sb["complexity_match"] <= 1.0
        assert 0.0 <= sb["inferred_demographics"] <= 1.0
        assert 0.0 <= sb["budget_fit"] <= 1.0
        assert isinstance(sb["inventory_available"], bool)
        assert len(r["reasons"]) >= 2
        assert r["mockup_hint"]["suggested_color"]
        assert r["price_paise"] > 0
        assert r["price_rupees"] == r["price_paise"] / 100
        assert r["units_available"] >= 0
        assert r["low_stock"] is (r["units_available"] < 5)

    # ------------------------------------------------------------------
    # GET /recommendations must return identical data (persistence check)
    # ------------------------------------------------------------------
    get_rec_resp = client.get(f"/api/v1/designs/{design_id}/recommendations")
    assert get_rec_resp.status_code == 200, get_rec_resp.text
    get_body = get_rec_resp.json()
    assert [r["product_id"] for r in get_body["recommendations"]] == [
        r["product_id"] for r in recs
    ]
    assert get_body["generated_at"] is not None

    # ------------------------------------------------------------------
    # MockProvider tool-call sequence
    # ------------------------------------------------------------------
    tool_calls = [call["tool_choice"] for call in llm.calls]
    assert "submit_story" in tool_calls
    assert "submit_design_strategy" in tool_calls
    assert "submit_recommendations" in tool_calls

    # ------------------------------------------------------------------
    # DB-level assertions (fresh engine, isolated event loop)
    # ------------------------------------------------------------------
    _run_db_assertions(design_id, session_id, design_pipeline_run_id)
