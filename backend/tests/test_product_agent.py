"""Unit tests for ProductAgent and ProductConfig registry — no DB, no API."""

from __future__ import annotations

import pytest

from app.agents.product import ProductAgent, _build_product_message, _parse_recommendations
from app.models.schemas import DesignStrategy, KeralaTheme, Story
from app.providers.mock import _DEFAULT_RECOMMENDATIONS_OUTPUT, MockProvider
from app.services.product_registry import PRODUCT_REGISTRY

# ---------------------------------------------------------------------------
# ProductConfig registry
# ---------------------------------------------------------------------------


def test_registry_loads_all_five_products():
    assert len(PRODUCT_REGISTRY) == 5


def test_registry_has_expected_product_ids():
    expected = {"standard_tshirt", "premium_tshirt", "tote_bag", "coffee_mug", "hoodie"}
    assert set(PRODUCT_REGISTRY.keys()) == expected


def test_registry_product_has_required_fields():
    pc = PRODUCT_REGISTRY["standard_tshirt"]
    assert pc.price_paise > 0
    assert pc.print_area_width_in > 0
    assert pc.print_area_height_in > 0
    assert len(pc.colors) > 0
    assert pc.production_time_min > 0
    assert len(pc.design_fit_scores) == 4
    assert "illustration" in pc.design_fit_scores


def test_registry_design_fit_scores_in_range():
    for pc in PRODUCT_REGISTRY.values():
        for score in pc.design_fit_scores.values():
            assert 0.0 <= score <= 1.0, f"{pc.product_id} score out of range"


def test_registry_mockup_colors_by_theme_complete():
    themes = [t.value for t in KeralaTheme if t != KeralaTheme.NONE]
    for pc in PRODUCT_REGISTRY.values():
        for theme in themes:
            assert theme in pc.suggested_colors_by_theme, (
                f"{pc.product_id} missing theme {theme}"
            )


def test_registry_default_color_in_colors():
    for pc in PRODUCT_REGISTRY.values():
        assert pc.default_color in pc.colors, (
            f"{pc.product_id} default_color '{pc.default_color}' not in colors"
        )


# ---------------------------------------------------------------------------
# _build_product_message
# ---------------------------------------------------------------------------


def _make_story() -> Story:
    return Story(
        themes=[KeralaTheme.BACKWATERS, KeralaTheme.FISHING_HERITAGE],
        emotions=["nostalgia", "pride"],
        keywords=["fishing_boat", "coconut_palm"],
        cultural_refs=["Kerala backwaters"],
        design_complexity="medium",
        intent="DESIGN_REQUEST",
        raw_customer_text="I grew up fishing on the backwaters of Alappuzha",
    )


def _make_strategy() -> DesignStrategy:
    return DesignStrategy(**{
        "base_story_summary": "Kerala backwaters fishing heritage.",
        "variants": [
            {
                "style": "illustration",
                "prompt": "test",
                "negative_prompt": "bad",
                "color_palette": ["#E8C547"],
                "mood": "warm",
                "width": 4000,
                "height": 4800,
            }
        ] * 4,
        "design_metadata": {
            "cultural_authenticity_score": 0.9,
            "print_feasibility": "excellent",
            "color_count": 4,
            "complexity": "medium",
            "estimated_print_time_min": 7.0,
            "kerala_themes_used": ["backwaters"],
        },
    })


def test_build_product_message_single_user_message():
    msgs = _build_product_message(_make_story(), _make_strategy(), PRODUCT_REGISTRY)
    assert len(msgs) == 1
    assert msgs[0].role == "user"


def test_build_product_message_contains_all_product_ids():
    content = _build_product_message(_make_story(), _make_strategy(), PRODUCT_REGISTRY)[0].content
    for pid in PRODUCT_REGISTRY:
        assert pid in content


def test_build_product_message_contains_story_fields():
    content = _build_product_message(_make_story(), _make_strategy(), PRODUCT_REGISTRY)[0].content
    assert "backwaters" in content
    assert "nostalgia" in content
    assert "medium" in content


# ---------------------------------------------------------------------------
# _parse_recommendations
# ---------------------------------------------------------------------------


def test_parse_recommendations_returns_three():
    recs = _parse_recommendations(_DEFAULT_RECOMMENDATIONS_OUTPUT, PRODUCT_REGISTRY)
    assert len(recs) == 3


def test_parse_recommendations_sorted_by_rank():
    recs = _parse_recommendations(_DEFAULT_RECOMMENDATIONS_OUTPUT, PRODUCT_REGISTRY)
    assert [r.rank for r in recs] == [1, 2, 3]


def test_parse_recommendations_fills_price_from_registry():
    recs = _parse_recommendations(_DEFAULT_RECOMMENDATIONS_OUTPUT, PRODUCT_REGISTRY)
    rank1 = recs[0]
    assert rank1.price_paise == PRODUCT_REGISTRY["standard_tshirt"].price_paise


def test_parse_recommendations_fills_print_area_from_registry():
    recs = _parse_recommendations(_DEFAULT_RECOMMENDATIONS_OUTPUT, PRODUCT_REGISTRY)
    assert recs[0].print_area_width_in > 0
    assert recs[0].print_area_height_in > 0


def test_parse_recommendations_has_reasons():
    recs = _parse_recommendations(_DEFAULT_RECOMMENDATIONS_OUTPUT, PRODUCT_REGISTRY)
    for r in recs:
        assert len(r.reasons) >= 2


def test_parse_recommendations_mockup_hint_present():
    recs = _parse_recommendations(_DEFAULT_RECOMMENDATIONS_OUTPUT, PRODUCT_REGISTRY)
    for r in recs:
        assert r.mockup_hint.suggested_color
        assert isinstance(r.mockup_hint.placement, str | None)


# ---------------------------------------------------------------------------
# ProductAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_product_agent_returns_three_recs():
    provider = MockProvider()
    agent = ProductAgent(provider=provider, registry=PRODUCT_REGISTRY)
    recs, _ = await agent.recommend(story=_make_story(), strategy=_make_strategy())
    assert len(recs) == 3


@pytest.mark.asyncio
async def test_product_agent_returns_metadata():
    provider = MockProvider()
    agent = ProductAgent(provider=provider, registry=PRODUCT_REGISTRY)
    _, meta = await agent.recommend(story=_make_story(), strategy=_make_strategy())
    assert "input_tokens" in meta
    assert "output_tokens" in meta
    assert "model_used" in meta
    assert "prompt_version" in meta


@pytest.mark.asyncio
async def test_product_agent_calls_correct_tool():
    provider = MockProvider()
    agent = ProductAgent(provider=provider, registry=PRODUCT_REGISTRY)
    await agent.recommend(story=_make_story(), strategy=_make_strategy())
    assert provider.calls[0]["tool_choice"] == "submit_recommendations"


@pytest.mark.asyncio
async def test_product_agent_prompt_version_is_sha1():
    provider = MockProvider()
    agent = ProductAgent(provider=provider, registry=PRODUCT_REGISTRY)
    assert len(agent.prompt_version) == 40


@pytest.mark.asyncio
async def test_product_agent_recs_ranked_1_to_3():
    provider = MockProvider()
    agent = ProductAgent(provider=provider, registry=PRODUCT_REGISTRY)
    recs, _ = await agent.recommend(story=_make_story(), strategy=_make_strategy())
    assert [r.rank for r in recs] == [1, 2, 3]


@pytest.mark.asyncio
async def test_product_agent_scores_in_range():
    provider = MockProvider()
    agent = ProductAgent(provider=provider, registry=PRODUCT_REGISTRY)
    recs, _ = await agent.recommend(story=_make_story(), strategy=_make_strategy())
    for r in recs:
        assert 0.0 <= r.score <= 1.0
        assert 0.0 <= r.score_breakdown.design_fit <= 1.0
        assert 0.0 <= r.score_breakdown.complexity_match <= 1.0
