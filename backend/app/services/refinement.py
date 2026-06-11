"""Refinement service — prompt augmentation and variant lineage management.

Refinement types map to specific prompt modifier instructions that are
appended to the original variant prompt before regeneration.

Rules:
  - Max 3 refinements per design (designs.refinements_count)
  - Each refinement creates a new variant row; originals are never modified
  - parent_variant_id tracks the lineage tree
  - Variant numbers continue from the highest existing number (5, 6, 7 …)
  - pipeline_run_id is preserved from the parent design for full trace lineage
"""

from __future__ import annotations

from enum import StrEnum


class RefinementType(StrEnum):
    MORE_MINIMAL = "more_minimal"
    MORE_CULTURAL = "more_cultural"
    MORE_MODERN = "more_modern"
    MORE_PREMIUM = "more_premium"
    DIFFERENT_COLOURS = "different_colours"
    DIFFERENT_LAYOUT = "different_layout"


# Maximum times a single design can be refined (not per-variant)
MAX_REFINEMENTS = 3

# Per-type prompt modifier appended to the original prompt
_REFINEMENT_MODIFIERS: dict[RefinementType, str] = {
    RefinementType.MORE_MINIMAL: (
        ", simplified composition, reduce to single focal element, "
        "maximum two colors, abundant negative space, stripped back"
    ),
    RefinementType.MORE_CULTURAL: (
        ", deeply rooted Kerala cultural iconography, traditional folk art motifs, "
        "authentic regional patterns, heritage craft aesthetic"
    ),
    RefinementType.MORE_MODERN: (
        ", contemporary graphic design aesthetic, clean geometric lines, "
        "modern typography-free illustration, bold contrast, urban feel"
    ),
    RefinementType.MORE_PREMIUM: (
        ", luxury brand aesthetic, gold foil effect, elevated composition, "
        "refined detail, premium fashion label style"
    ),
    RefinementType.DIFFERENT_COLOURS: (
        ", completely new color palette, shift hue range by 120 degrees, "
        "fresh complementary tones, do not reuse original palette colors"
    ),
    RefinementType.DIFFERENT_LAYOUT: (
        ", recompose the scene entirely, portrait to landscape orientation shift, "
        "new focal point placement, different visual hierarchy, alternate framing"
    ),
}

# Per-type negative prompt additions
_REFINEMENT_NEG_ADDITIONS: dict[RefinementType, str] = {
    RefinementType.MORE_MINIMAL: ", complex details, multiple elements, busy composition",
    RefinementType.MORE_CULTURAL: ", generic, western, non-Kerala, tourist cliche",
    RefinementType.MORE_MODERN: ", vintage, retro, aged, distressed, antiquated",
    RefinementType.MORE_PREMIUM: ", cheap, gaudy, low quality, over-saturated",
    RefinementType.DIFFERENT_COLOURS: "",
    RefinementType.DIFFERENT_LAYOUT: "",
}


def build_refined_prompt(
    original_prompt: str,
    original_negative: str | None,
    refinement_type: RefinementType,
) -> tuple[str, str]:
    """Return (refined_prompt, refined_negative_prompt) for a given refinement type."""
    modifier = _REFINEMENT_MODIFIERS[refinement_type]
    neg_addition = _REFINEMENT_NEG_ADDITIONS[refinement_type]
    refined = original_prompt.rstrip() + modifier
    base_neg = original_negative or "photorealistic, photograph, 3d render, blurry, low quality"
    refined_neg = base_neg + neg_addition
    return refined, refined_neg
