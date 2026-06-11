"""Product Recommendation Agent.

Scores BOBB product catalogue against Story + DesignStrategy using tool_use.
Uses claude-haiku-4-5-20251001 (fast, cheaper) per CLAUDE.md agent design principles.
Returns top-3 ProductRecommendation objects with score breakdowns and explanations.

Never parse Claude text — always consume the tool_use block.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.logging import get_logger
from app.models.schemas import (
    DesignStrategy,
    MockupHint,
    ProductRecommendation,
    ScoreBreakdown,
    Story,
)
from app.providers.base import LLMProvider, Message, ToolDefinition
from app.services.product_registry import PRODUCT_REGISTRY, ProductConfig

logger = get_logger("agent.product")

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "product.txt"

_SUBMIT_RECOMMENDATIONS_TOOL = ToolDefinition(
    name="submit_recommendations",
    description="Submit exactly 3 ranked product recommendations for this customer's design.",
    input_schema={
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer", "minimum": 1, "maximum": 3},
                        "product_id": {"type": "string"},
                        "product_name": {"type": "string"},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "score_breakdown": {
                            "type": "object",
                            "properties": {
                                "design_fit": {"type": "number", "minimum": 0, "maximum": 1},
                                "complexity_match": {
                                    "type": "number", "minimum": 0, "maximum": 1
                                },
                                "inferred_demographics": {
                                    "type": "number", "minimum": 0, "maximum": 1
                                },
                                "budget_fit": {"type": "number", "minimum": 0, "maximum": 1},
                                "inventory_available": {"type": "boolean"},
                            },
                            "required": [
                                "design_fit",
                                "complexity_match",
                                "inferred_demographics",
                                "budget_fit",
                                "inventory_available",
                            ],
                        },
                        "reasons": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 4,
                        },
                        "mockup_hint": {
                            "type": "object",
                            "properties": {
                                "suggested_color": {"type": "string"},
                                "suggested_size": {"type": ["string", "null"]},
                                "placement": {"type": ["string", "null"]},
                            },
                            "required": ["suggested_color", "suggested_size", "placement"],
                        },
                    },
                    "required": [
                        "rank",
                        "product_id",
                        "product_name",
                        "score",
                        "score_breakdown",
                        "reasons",
                        "mockup_hint",
                    ],
                },
                "description": "Exactly 3 product recommendations ranked 1-3.",
            }
        },
        "required": ["recommendations"],
    },
)


def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _prompt_version(system_prompt: str) -> str:
    return hashlib.sha1(system_prompt.encode()).hexdigest()


def _build_product_message(
    story: Story,
    strategy: DesignStrategy,
    registry: dict[str, ProductConfig],
) -> list[Message]:
    """Build the single-turn message with story, design, and full product catalogue."""
    # Dominant style from first variant (used for design_fit score lookup)
    dominant_style = strategy.variants[0].style.value if strategy.variants else "illustration"

    catalogue_items = []
    for pc in registry.values():
        style_fit = pc.design_fit_scores.get(dominant_style, 0.8)
        units_avail = max(0, pc.units_total)
        catalogue_items.append(
            f"- {pc.product_id} | {pc.product_name} | ₹{pc.price_paise // 100} "
            f"| print {pc.print_area_width_in}×{pc.print_area_height_in}in "
            f"| complexity {pc.min_complexity}-{pc.max_complexity} "
            f"| style_fit ({dominant_style}): {style_fit:.2f} "
            f"| units_available: {units_avail} "
            f"| colors: {', '.join(pc.colors[:3])} "
            f"| best_for: {pc.best_for}"
        )
    catalogue_text = "\n".join(catalogue_items)

    content = (
        f"## Customer Story\n"
        f"Raw text: {story.raw_customer_text}\n"
        f"Themes: {', '.join(story.themes)}\n"
        f"Emotions: {', '.join(story.emotions)}\n"
        f"Design complexity: {story.design_complexity}\n"
        f"Intent: {story.intent}\n\n"
        f"## Design Strategy\n"
        f"Summary: {strategy.base_story_summary}\n"
        f"Dominant style: {dominant_style}\n"
        f"Print feasibility: {strategy.design_metadata.print_feasibility}\n"
        f"Color count: {strategy.design_metadata.color_count}\n\n"
        f"## Product Catalogue\n"
        f"{catalogue_text}\n\n"
        "Score all products above and return EXACTLY 3 recommendations ranked best to worst."
    )
    return [Message(role="user", content=content)]


def _parse_recommendations(
    tool_input: dict[str, Any],
    registry: dict[str, ProductConfig],
) -> list[ProductRecommendation]:
    """Map tool output to ProductRecommendation Pydantic models.

    Merges price/print-area from registry; falls back to tool-provided values
    if a product_id is unknown (future extensibility).
    """
    results: list[ProductRecommendation] = []
    for raw in tool_input["recommendations"]:
        pid = raw["product_id"]
        pc = registry.get(pid)

        score_b = raw["score_breakdown"]
        breakdown = ScoreBreakdown(
            design_fit=score_b["design_fit"],
            complexity_match=score_b["complexity_match"],
            inferred_demographics=score_b["inferred_demographics"],
            budget_fit=score_b["budget_fit"],
            inventory_available=score_b["inventory_available"],
        )

        hint_raw = raw["mockup_hint"]
        mockup = MockupHint(
            suggested_color=hint_raw["suggested_color"],
            suggested_size=hint_raw.get("suggested_size"),
            placement=hint_raw.get("placement"),
        )

        results.append(
            ProductRecommendation(
                rank=raw["rank"],
                product_id=pid,
                product_name=raw["product_name"],
                score=raw["score"],
                score_breakdown=breakdown,
                reasons=raw["reasons"],
                price_paise=pc.price_paise if pc else 0,
                print_area_width_in=pc.print_area_width_in if pc else 0.0,
                print_area_height_in=pc.print_area_height_in if pc else 0.0,
                production_time_minutes=pc.production_time_min if pc else 0,
                mockup_hint=mockup,
                units_available=max(0, pc.units_total) if pc else 0,
            )
        )
    return sorted(results, key=lambda r: r.rank)


class ProductAgent:
    """Scores product catalogue against Story+DesignStrategy using Claude Haiku."""

    MODEL = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        provider: LLMProvider,
        registry: dict[str, ProductConfig] | None = None,
    ) -> None:
        self._provider = provider
        self._registry = registry if registry is not None else PRODUCT_REGISTRY
        self._system_prompt = _load_system_prompt()
        self._prompt_ver = _prompt_version(self._system_prompt)

    @property
    def prompt_version(self) -> str:
        return self._prompt_ver

    async def recommend(
        self,
        story: Story,
        strategy: DesignStrategy,
    ) -> tuple[list[ProductRecommendation], dict[str, Any]]:
        """Return top-3 ProductRecommendations and metadata for agent_logs persistence.

        Returns:
            (recommendations, metadata) where metadata has token counts, model,
            prompt_version for agent_logs.

        Raises:
            ValidationError: tool output fails schema validation.
            Exception: provider-level errors.
        """
        messages = _build_product_message(story, strategy, self._registry)

        response = await self._provider.create_message(
            system=self._system_prompt,
            messages=messages,
            tools=[_SUBMIT_RECOMMENDATIONS_TOOL],
            tool_choice="submit_recommendations",
            max_tokens=1024,
        )

        logger.info(
            "product_agent_response",
            tool=response.tool_name,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model=response.model,
            prompt_version=self._prompt_ver,
        )

        try:
            recs = _parse_recommendations(response.tool_input, self._registry)
        except (ValidationError, KeyError, ValueError) as exc:
            logger.error(
                "product_recommendations_validation_failed",
                error=str(exc),
                raw_tool_input=response.tool_input,
            )
            raise

        metadata: dict[str, Any] = {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "model_used": response.model,
            "prompt_version": self._prompt_ver,
        }
        return recs, metadata
