"""Design Strategy Agent.

Translates Story intelligence into a DesignStrategy with 4 variant prompts
(illustration, geometric, watercolor, minimalist) ready for image generation.

Uses tool_use exclusively — never parses Claude text.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.logging import get_logger
from app.models.schemas import (
    DesignMetadata,
    DesignStrategy,
    KeralaTheme,
    Story,
    VariantPrompt,
    VariantStyle,
)
from app.providers.base import LLMProvider, Message, ToolDefinition

logger = get_logger("agent.design")

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "design.txt"

_SUBMIT_DESIGN_STRATEGY_TOOL = ToolDefinition(
    name="submit_design_strategy",
    description="Submit the complete design strategy with 4 variant prompts.",
    input_schema={
        "type": "object",
        "properties": {
            "base_story_summary": {
                "type": "string",
                "description": "One-sentence visual design brief for display and logging.",
            },
            "primary_kerala_theme": {
                "type": "string",
                "enum": [t.value for t in KeralaTheme],
                "description": "The single dominant Kerala theme driving the composition.",
            },
            "primary_emotion": {
                "type": "string",
                "description": "Strongest emotion from the story (nostalgia, pride, joy, etc.).",
            },
            "key_symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 visual symbols appearing in at least one variant.",
                "minItems": 1,
                "maxItems": 6,
            },
            "variants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "style": {
                            "type": "string",
                            "enum": [s.value for s in VariantStyle],
                        },
                        "prompt": {
                            "type": "string",
                            "description": "40-80 word positive image generation prompt.",
                        },
                        "negative_prompt": {
                            "type": "string",
                            "description": "Full negative prompt including DTF base negatives.",
                        },
                        "color_palette": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "3-6 hex codes or named colors from BOBB palette.",
                        },
                        "mood": {
                            "type": "string",
                            "description": "2-4 word mood descriptor for UI display.",
                        },
                        "width": {"type": "integer", "description": "Pixel width."},
                        "height": {"type": "integer", "description": "Pixel height."},
                    },
                    "required": [
                        "style",
                        "prompt",
                        "negative_prompt",
                        "color_palette",
                        "mood",
                        "width",
                        "height",
                    ],
                },
                "minItems": 4,
                "maxItems": 4,
                "description": "Exactly 4 variant prompts, one per style.",
            },
            "design_metadata": {
                "type": "object",
                "properties": {
                    "cultural_authenticity_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "print_feasibility": {
                        "type": "string",
                        "enum": ["excellent", "good", "marginal", "poor"],
                    },
                    "color_count": {"type": "integer"},
                    "complexity": {
                        "type": "string",
                        "enum": ["simple", "medium", "complex"],
                    },
                    "estimated_print_time_min": {"type": "number"},
                    "kerala_themes_used": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [t.value for t in KeralaTheme],
                        },
                    },
                },
                "required": [
                    "cultural_authenticity_score",
                    "print_feasibility",
                    "color_count",
                    "complexity",
                    "estimated_print_time_min",
                    "kerala_themes_used",
                ],
            },
            "product_suitability": {
                "type": "object",
                "additionalProperties": {"type": "number"},
                "description": "Product ID -> suitability score 0.0-1.0.",
            },
        },
        "required": [
            "base_story_summary",
            "primary_kerala_theme",
            "primary_emotion",
            "key_symbols",
            "variants",
            "design_metadata",
            "product_suitability",
        ],
    },
)


def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _prompt_version(system_prompt: str) -> str:
    return hashlib.sha1(system_prompt.encode()).hexdigest()


def _build_design_message(story: Story) -> list[Message]:
    """Build the single-turn message containing the story intelligence."""
    story_text = (
        f"Customer story: {story.raw_customer_text}\n\n"
        f"Themes: {', '.join(story.themes)}\n"
        f"Emotions: {', '.join(story.emotions)}\n"
        f"Key symbols: {', '.join(story.keywords)}\n"
        f"Cultural references: {', '.join(story.cultural_refs)}\n"
        f"Design complexity: {story.design_complexity}\n"
        f"Intent: {story.intent}"
    )
    return [Message(role="user", content=story_text)]


def _parse_design_strategy(tool_input: dict[str, Any]) -> DesignStrategy:
    """Validate and map tool output to DesignStrategy Pydantic schema."""
    variants = [
        VariantPrompt(
            style=VariantStyle(v["style"]),
            prompt=v["prompt"],
            negative_prompt=v["negative_prompt"],
            color_palette=v["color_palette"],
            mood=v["mood"],
            width=v["width"],
            height=v["height"],
        )
        for v in tool_input["variants"]
    ]

    metadata_raw = tool_input["design_metadata"]
    design_metadata = DesignMetadata(
        cultural_authenticity_score=metadata_raw["cultural_authenticity_score"],
        print_feasibility=metadata_raw["print_feasibility"],
        color_count=metadata_raw["color_count"],
        complexity=metadata_raw["complexity"],
        estimated_print_time_min=metadata_raw["estimated_print_time_min"],
        kerala_themes_used=[KeralaTheme(t) for t in metadata_raw["kerala_themes_used"]],
    )

    return DesignStrategy(
        base_story_summary=tool_input["base_story_summary"],
        variants=variants,
        design_metadata=design_metadata,
    )


class DesignAgent:
    """Translates Story into DesignStrategy using Claude tool_use."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider
        self._system_prompt = _load_system_prompt()
        self._prompt_ver = _prompt_version(self._system_prompt)

    @property
    def prompt_version(self) -> str:
        return self._prompt_ver

    async def generate_strategy(
        self,
        story: Story,
    ) -> tuple[DesignStrategy, dict[str, Any]]:
        """Generate a DesignStrategy from the given Story.

        Returns:
            (DesignStrategy, metadata) where metadata contains token counts,
            model name, prompt_version, primary_kerala_theme, primary_emotion,
            key_symbols, and product_suitability for persistence.

        Raises:
            ValidationError: tool output fails DesignStrategy schema validation.
            Exception: Provider-level errors.
        """
        messages = _build_design_message(story)

        response = await self._provider.create_message(
            system=self._system_prompt,
            messages=messages,
            tools=[_SUBMIT_DESIGN_STRATEGY_TOOL],
            tool_choice="submit_design_strategy",
            max_tokens=2048,
        )

        logger.info(
            "design_agent_response",
            tool=response.tool_name,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model=response.model,
            prompt_version=self._prompt_ver,
        )

        try:
            strategy = _parse_design_strategy(response.tool_input)
        except (ValidationError, KeyError, ValueError) as exc:
            logger.error(
                "design_strategy_validation_failed",
                error=str(exc),
                raw_tool_input=response.tool_input,
            )
            raise

        metadata: dict[str, Any] = {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "model_used": response.model,
            "prompt_version": self._prompt_ver,
            "primary_kerala_theme": response.tool_input.get("primary_kerala_theme"),
            "primary_emotion": response.tool_input.get("primary_emotion"),
            "key_symbols": response.tool_input.get("key_symbols", []),
            "product_suitability": response.tool_input.get("product_suitability", {}),
        }
        return strategy, metadata
