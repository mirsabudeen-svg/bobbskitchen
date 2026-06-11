"""Unit tests for refinement service — prompt building, type coverage."""

from __future__ import annotations

import pytest

from app.services.refinement import (
    MAX_REFINEMENTS,
    RefinementType,
    build_refined_prompt,
)


def test_max_refinements_is_three():
    assert MAX_REFINEMENTS == 3


def test_all_refinement_types_have_modifiers():
    for rtype in RefinementType:
        prompt, neg = build_refined_prompt(
            original_prompt="Kerala boat illustration",
            original_negative="photorealistic, blurry",
            refinement_type=rtype,
        )
        assert len(prompt) > len("Kerala boat illustration"), (
            f"{rtype} modifier should lengthen the prompt"
        )
        assert isinstance(neg, str)
        assert len(neg) > 0


def test_build_refined_prompt_appends_to_original():
    original = "Kerala backwaters illustration, bold outlines"
    prompt, _ = build_refined_prompt(
        original_prompt=original,
        original_negative="blurry",
        refinement_type=RefinementType.MORE_MINIMAL,
    )
    assert prompt.startswith(original)


def test_build_refined_prompt_preserves_negative():
    orig_neg = "photorealistic, blurry, low quality"
    _, neg = build_refined_prompt(
        original_prompt="test prompt",
        original_negative=orig_neg,
        refinement_type=RefinementType.MORE_MODERN,
    )
    assert orig_neg in neg


def test_build_refined_prompt_uses_default_negative_when_none():
    _, neg = build_refined_prompt(
        original_prompt="test prompt",
        original_negative=None,
        refinement_type=RefinementType.MORE_CULTURAL,
    )
    assert "photorealistic" in neg


@pytest.mark.parametrize(
    "rtype,expected_keyword",
    [
        (RefinementType.MORE_MINIMAL, "single focal element"),
        (RefinementType.MORE_CULTURAL, "Kerala cultural iconography"),
        (RefinementType.MORE_MODERN, "contemporary"),
        (RefinementType.MORE_PREMIUM, "luxury"),
        (RefinementType.DIFFERENT_COLOURS, "color palette"),
        (RefinementType.DIFFERENT_LAYOUT, "recompose"),
    ],
)
def test_refinement_type_modifier_contains_keyword(rtype, expected_keyword):
    prompt, _ = build_refined_prompt(
        original_prompt="base prompt",
        original_negative="bad",
        refinement_type=rtype,
    )
    assert expected_keyword in prompt


def test_more_minimal_adds_negative_terms():
    _, neg = build_refined_prompt(
        original_prompt="test",
        original_negative="photorealistic",
        refinement_type=RefinementType.MORE_MINIMAL,
    )
    assert "complex details" in neg or "busy composition" in neg


def test_more_modern_adds_negative_terms():
    _, neg = build_refined_prompt(
        original_prompt="test",
        original_negative="photorealistic",
        refinement_type=RefinementType.MORE_MODERN,
    )
    assert "vintage" in neg or "retro" in neg
