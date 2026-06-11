"""Unit tests for DesignAgent — no DB, no API, no Anthropic calls."""

from __future__ import annotations

import pytest

from app.agents.design import DesignAgent, _build_design_message, _parse_design_strategy
from app.models.schemas import DesignStrategy, KeralaTheme, Story, VariantStyle
from app.providers.mock import _DEFAULT_DESIGN_STRATEGY_OUTPUT, MockProvider


def _make_story(**kwargs) -> Story:
    defaults = {
        "themes": [KeralaTheme.BACKWATERS, KeralaTheme.FISHING_HERITAGE],
        "emotions": ["nostalgia", "pride"],
        "keywords": ["fishing_boat", "coconut_palm"],
        "cultural_refs": ["Kerala backwaters"],
        "design_complexity": "medium",
        "intent": "DESIGN_REQUEST",
        "raw_customer_text": "I grew up fishing on the backwaters of Alappuzha",
    }
    defaults.update(kwargs)
    return Story(**defaults)


# ---------------------------------------------------------------------------
# _build_design_message
# ---------------------------------------------------------------------------


def test_build_design_message_single_message():
    story = _make_story()
    messages = _build_design_message(story)
    assert len(messages) == 1
    assert messages[0].role == "user"


def test_build_design_message_contains_story_fields():
    story = _make_story()
    messages = _build_design_message(story)
    content = messages[0].content
    assert "backwaters" in content
    assert "nostalgia" in content
    assert "fishing_boat" in content
    assert story.raw_customer_text in content


def test_build_design_message_contains_complexity():
    story = _make_story(design_complexity="complex")
    messages = _build_design_message(story)
    assert "complex" in messages[0].content


# ---------------------------------------------------------------------------
# _parse_design_strategy
# ---------------------------------------------------------------------------


def test_parse_design_strategy_returns_design_strategy():
    strategy = _parse_design_strategy(_DEFAULT_DESIGN_STRATEGY_OUTPUT)
    assert isinstance(strategy, DesignStrategy)


def test_parse_design_strategy_has_four_variants():
    strategy = _parse_design_strategy(_DEFAULT_DESIGN_STRATEGY_OUTPUT)
    assert len(strategy.variants) == 4


def test_parse_design_strategy_all_styles_present():
    strategy = _parse_design_strategy(_DEFAULT_DESIGN_STRATEGY_OUTPUT)
    styles = {v.style for v in strategy.variants}
    assert styles == {
        VariantStyle.ILLUSTRATION,
        VariantStyle.GEOMETRIC,
        VariantStyle.WATERCOLOR,
        VariantStyle.MINIMALIST,
    }


def test_parse_design_strategy_metadata_valid():
    strategy = _parse_design_strategy(_DEFAULT_DESIGN_STRATEGY_OUTPUT)
    meta = strategy.design_metadata
    assert 0.0 <= meta.cultural_authenticity_score <= 1.0
    assert meta.print_feasibility in {"excellent", "good", "marginal", "poor"}
    assert meta.complexity in {"simple", "medium", "complex"}
    assert meta.color_count > 0


def test_parse_design_strategy_kerala_themes_are_enum():
    strategy = _parse_design_strategy(_DEFAULT_DESIGN_STRATEGY_OUTPUT)
    for theme in strategy.design_metadata.kerala_themes_used:
        assert isinstance(theme, KeralaTheme)


def test_parse_design_strategy_variants_have_prompts():
    strategy = _parse_design_strategy(_DEFAULT_DESIGN_STRATEGY_OUTPUT)
    for variant in strategy.variants:
        assert len(variant.prompt) > 20
        assert len(variant.negative_prompt) > 10
        assert len(variant.color_palette) >= 2
        assert variant.width > 0
        assert variant.height > 0


# ---------------------------------------------------------------------------
# DesignAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_design_agent_returns_strategy():
    provider = MockProvider()
    agent = DesignAgent(provider=provider)
    story = _make_story()
    strategy, meta = await agent.generate_strategy(story=story)
    assert isinstance(strategy, DesignStrategy)
    assert len(strategy.variants) == 4


@pytest.mark.asyncio
async def test_design_agent_returns_metadata():
    provider = MockProvider()
    agent = DesignAgent(provider=provider)
    story = _make_story()
    _, meta = await agent.generate_strategy(story=story)
    assert "input_tokens" in meta
    assert "output_tokens" in meta
    assert "model_used" in meta
    assert "prompt_version" in meta
    assert "primary_kerala_theme" in meta
    assert "primary_emotion" in meta
    assert "key_symbols" in meta
    assert "product_suitability" in meta


@pytest.mark.asyncio
async def test_design_agent_calls_correct_tool():
    provider = MockProvider()
    agent = DesignAgent(provider=provider)
    story = _make_story()
    await agent.generate_strategy(story=story)
    assert len(provider.calls) == 1
    assert provider.calls[0]["tool_choice"] == "submit_design_strategy"


@pytest.mark.asyncio
async def test_design_agent_prompt_version_is_sha1():
    provider = MockProvider()
    agent = DesignAgent(provider=provider)
    assert len(agent.prompt_version) == 40  # SHA-1 hex digest length


@pytest.mark.asyncio
async def test_design_agent_max_tokens_2048():
    provider = MockProvider()
    agent = DesignAgent(provider=provider)
    await agent.generate_strategy(story=_make_story())
    assert provider.calls[0]["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_design_agent_passes_story_to_provider():
    provider = MockProvider()
    agent = DesignAgent(provider=provider)
    story = _make_story(raw_customer_text="unique test story text xyz")
    await agent.generate_strategy(story=story)
    message_content = provider.calls[0]["messages"][0].content
    assert "unique test story text xyz" in message_content


@pytest.mark.asyncio
async def test_design_agent_product_suitability_scores():
    provider = MockProvider()
    agent = DesignAgent(provider=provider)
    _, meta = await agent.generate_strategy(story=_make_story())
    suitability = meta["product_suitability"]
    assert isinstance(suitability, dict)
    assert "standard_tshirt" in suitability
    for score in suitability.values():
        assert 0.0 <= score <= 1.0
