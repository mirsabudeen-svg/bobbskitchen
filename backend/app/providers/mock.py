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
            {"submit_story": _DEFAULT_STORY_OUTPUT} if responses is None else responses
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
