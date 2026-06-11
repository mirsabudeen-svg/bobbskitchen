"""LLM provider abstraction.

All agents call LLMProvider.create_message() — never the Anthropic SDK directly.
This keeps the Anthropic SDK import behind one seam, enabling:
  - MockProvider in tests (no API keys, deterministic responses)
  - Future provider swaps (OpenAI-compatible, etc.)

Tool-use pattern:
  Pass tools= and tool_choice= to force Claude to call exactly one tool.
  The response content will contain a ToolUseBlock with the structured output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    tool_name: str
    tool_input: dict[str, Any]   # parsed JSON from tool_use block
    input_tokens: int
    output_tokens: int
    model: str
    stop_reason: str             # "tool_use" on success


class LLMProvider(Protocol):
    async def create_message(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolDefinition],
        tool_choice: str,        # name of the tool to force-call
        max_tokens: int = 1024,
    ) -> LLMResponse:
        ...
