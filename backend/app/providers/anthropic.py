"""Anthropic Claude provider implementation.

Uses the tool_use API to force structured JSON output from every agent call.
Never parse Claude's text responses — always use tool_use.
"""

from __future__ import annotations

import anthropic

from app.providers.base import LLMProvider, LLMResponse, Message, ToolDefinition


class AnthropicProvider:
    """Wraps the Anthropic SDK. Implements LLMProvider protocol."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def create_message(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolDefinition],
        tool_choice: str,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        anthropic_tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]
        anthropic_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        response = await self._client.messages.create(  # type: ignore[call-overload]
            model=self._model,
            system=system,
            messages=anthropic_messages,
            tools=anthropic_tools,
            tool_choice={"type": "tool", "name": tool_choice},
            max_tokens=max_tokens,
        )

        # Find the tool_use block — guaranteed present when tool_choice is forced.
        tool_block = next(
            block for block in response.content if block.type == "tool_use"
        )

        return LLMResponse(
            tool_name=tool_block.name,
            tool_input=tool_block.input,  # type: ignore[arg-type]
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
            stop_reason=response.stop_reason or "tool_use",
        )


def make_anthropic_provider(api_key: str, model: str) -> LLMProvider:
    return AnthropicProvider(api_key=api_key, model=model)
