"""Mock LLM provider for development and testing.

Returns deterministic responses without making any API calls.
Registered via IMAGE_GEN_PROVIDER=mock or directly in tests.

Usage:
    provider = MockProvider(responses={"submit_story": {...}})
    provider = MockProvider()  # uses built-in Kerala story defaults
"""

from __future__ import annotations

from typing import Any

from app.providers.base import LLMProvider, LLMResponse, Message, ToolDefinition

_DEFAULT_DESIGN_STRATEGY_OUTPUT: dict[str, Any] = {
    "base_story_summary": "Kerala backwaters fishing heritage rendered in four distinct styles.",
    "primary_kerala_theme": "backwaters",
    "primary_emotion": "nostalgia",
    "key_symbols": ["fishing_boat", "coconut_palm", "sunset"],
    "variants": [
        {
            "style": "illustration",
            "prompt": (
                "Kerala backwaters folk art illustration, traditional vallam fishing boat "
                "on still water at sunset, coconut palms silhouette, bold outlines, "
                "flat colour fills, warm gold #E8C547 and deep navy #0A1A3F palette"
            ),
            "negative_prompt": (
                "photorealistic, photograph, 3d render, blurry, low quality, watermark, "
                "text overlay, fine gradients, photographic face, realistic skin, NSFW"
            ),
            "color_palette": ["#E8C547", "#0A1A3F", "#2D6A4F", "#FAF7F0"],
            "mood": "warm nostalgia",
            "width": 4000,
            "height": 4800,
        },
        {
            "style": "geometric",
            "prompt": (
                "Geometric abstract Kerala backwaters, angular tessellation of boat and "
                "palm shapes, bold chevron water reflections, deep navy #0A1A3F background, "
                "gold #E8C547 geometric accents, modern design, clean lines"
            ),
            "negative_prompt": (
                "photorealistic, photograph, 3d render, blurry, low quality, watermark, "
                "text overlay, fine gradients, photographic face, realistic skin, NSFW, "
                "organic curves"
            ),
            "color_palette": ["#0A1A3F", "#E8C547", "#FAF7F0"],
            "mood": "modern heritage",
            "width": 4000,
            "height": 4800,
        },
        {
            "style": "watercolor",
            "prompt": (
                "Watercolour Kerala backwaters, bold wet-on-wet washes, fishing boat at "
                "golden hour, visible brushwork, vibrant saffron #E8833A sky, Kerala "
                "green #2D6A4F reflections, artistic loose style, expressive"
            ),
            "negative_prompt": (
                "photorealistic, photograph, 3d render, blurry, low quality, watermark, "
                "text overlay, photographic face, realistic skin, NSFW, soft gradients"
            ),
            "color_palette": ["#E8833A", "#2D6A4F", "#E8C547", "#0A1A3F", "#FAF7F0"],
            "mood": "golden hour",
            "width": 4000,
            "height": 4800,
        },
        {
            "style": "minimalist",
            "prompt": (
                "Minimalist Kerala fishing boat silhouette, single vallam on horizon line, "
                "cream #FAF7F0 background, deep navy #0A1A3F silhouette, 2 colours, "
                "clean negative space, bold simple icon"
            ),
            "negative_prompt": (
                "photorealistic, photograph, 3d render, blurry, low quality, watermark, "
                "text overlay, fine gradients, photographic face, realistic skin, NSFW, "
                "complex details, multiple elements"
            ),
            "color_palette": ["#FAF7F0", "#0A1A3F"],
            "mood": "calm simplicity",
            "width": 4000,
            "height": 4800,
        },
    ],
    "design_metadata": {
        "cultural_authenticity_score": 0.92,
        "print_feasibility": "excellent",
        "color_count": 5,
        "complexity": "medium",
        "estimated_print_time_min": 7.0,
        "kerala_themes_used": ["backwaters", "fishing_heritage"],
    },
    "product_suitability": {
        "standard_tshirt": 0.95,
        "premium_tshirt": 0.85,
        "tote_bag": 0.70,
        "coffee_mug": 0.40,
        "hoodie": 0.80,
    },
}

_DEFAULT_STORY_OUTPUT: dict[str, Any] = {
    "themes": ["backwaters", "fishing_heritage"],
    "emotions": ["nostalgia", "pride"],
    "symbols": ["fishing_boat", "coconut_palm", "sunset"],
    "cultural_elements": ["Kerala backwaters", "traditional fishing net"],
    "design_complexity": "medium",
    "intent": "DESIGN_REQUEST",
    "needs_clarification": False,
    "clarification_question": None,
    "raw_customer_text": "mock input",
    "confidence": 0.92,
    "clarity_score": 0.88,
}


class MockProvider:
    """Deterministic provider for tests. Raises if an unexpected tool is called."""

    def __init__(self, responses: dict[str, dict[str, Any]] | None = None) -> None:
        self._responses: dict[str, dict[str, Any]] = (
            {
                "submit_story": _DEFAULT_STORY_OUTPUT,
                "submit_design_strategy": _DEFAULT_DESIGN_STRATEGY_OUTPUT,
            }
            if responses is None
            else responses
        )
        self.calls: list[dict[str, Any]] = []  # introspectable in tests

    async def create_message(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolDefinition],
        tool_choice: str,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.calls.append(
            {
                "system": system,
                "messages": messages,
                "tool_choice": tool_choice,
                "max_tokens": max_tokens,
            }
        )
        if tool_choice not in self._responses:
            raise ValueError(
                f"MockProvider has no canned response for tool '{tool_choice}'. "
                f"Available: {list(self._responses)}"
            )
        return LLMResponse(
            tool_name=tool_choice,
            tool_input=self._responses[tool_choice],
            input_tokens=150,
            output_tokens=80,
            model="mock",
            stop_reason="tool_use",
        )


def make_mock_provider(responses: dict[str, dict[str, Any]] | None = None) -> LLMProvider:
    return MockProvider(responses=responses)
