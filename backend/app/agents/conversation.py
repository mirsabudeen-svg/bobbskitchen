"""Conversation (Story Intelligence) Agent.

Extracts structured Story from customer free-form text using tool_use.
Multi-turn: reconstructs full conversation history from ConversationTurn list
so Claude has context across clarification turns (FIX ISSUE-01).

Never parse Claude's text — always consume the tool_use block.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.logging import get_logger
from app.models.schemas import ConversationTurn, KeralaTheme, Story
from app.providers.base import LLMProvider, Message, ToolDefinition

logger = get_logger("agent.conversation")

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "conversation.txt"

# Tool schema: what Claude must produce via submit_story
_SUBMIT_STORY_TOOL = ToolDefinition(
    name="submit_story",
    description="Submit the structured story extracted from the customer's input.",
    input_schema={
        "type": "object",
        "properties": {
            "themes": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [t.value for t in KeralaTheme],
                },
                "description": "Kerala cultural themes present in the story.",
            },
            "emotions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Emotional tones: nostalgia, pride, love, joy, melancholy.",  # noqa: E501
            },
            "symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Visual symbols: fishing_boat, coconut_palm, temple_lamp.",
            },
            "cultural_elements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Named refs: Kerala backwaters, Nehru Trophy, etc.",
            },
            "design_complexity": {
                "type": "string",
                "enum": ["simple", "medium", "complex"],
                "description": "Complexity tier based on richness of story.",
            },
            "intent": {
                "type": "string",
                "enum": ["DESIGN_REQUEST", "GIFT", "MEMORY", "CELEBRATION", "OTHER"],
                "description": "Customer's design intent.",
            },
            "needs_clarification": {
                "type": "boolean",
                "description": "True only if the story is too ambiguous for design.",
            },
            "clarification_question": {
                "type": ["string", "null"],
                "description": "ONE focused question if needs_clarification; null otherwise.",
            },
            "raw_customer_text": {
                "type": "string",
                "description": "The customer's original unmodified input text.",
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Agent confidence in the extracted story (0.0-1.0).",
            },
            "clarity_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "How complete and unambiguous the story is (0.0-1.0).",
            },
        },
        "required": [
            "themes",
            "emotions",
            "symbols",
            "cultural_elements",
            "design_complexity",
            "intent",
            "needs_clarification",
            "clarification_question",
            "raw_customer_text",
            "confidence",
            "clarity_score",
        ],
    },
)


def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _prompt_version(system_prompt: str) -> str:
    """SHA-1 of the system prompt for agent_logs.prompt_version."""
    return hashlib.sha1(system_prompt.encode()).hexdigest()


def _build_messages(
    new_input: str,
    prior_turns: list[ConversationTurn],
) -> list[Message]:
    """Reconstruct full conversation history for multi-turn context (FIX ISSUE-01).

    Each prior turn becomes a user message + optional assistant message
    (the clarification question Claude asked). The new input is appended last.
    """
    messages: list[Message] = []
    for turn in prior_turns:
        messages.append(Message(role="user", content=turn.customer_input))
        if turn.agent_text_reply:
            messages.append(Message(role="assistant", content=turn.agent_text_reply))
    messages.append(Message(role="user", content=new_input))
    return messages


def _parse_story(tool_input: dict[str, Any], new_input: str) -> Story:
    """Validate tool output against the Story Pydantic schema.

    Fills raw_customer_text from new_input if the agent omitted it.
    Raises ValidationError if the output is structurally invalid.
    """
    if not tool_input.get("raw_customer_text"):
        tool_input = {**tool_input, "raw_customer_text": new_input}
    # Map tool output fields to Story schema fields
    story_data = {
        "themes": tool_input.get("themes", []),
        "emotions": tool_input.get("emotions", []),
        "keywords": tool_input.get("symbols", []),    # Story.keywords ← tool symbols
        "cultural_refs": tool_input.get("cultural_elements", []),
        "design_complexity": tool_input.get("design_complexity", "medium"),
        "intent": tool_input.get("intent", "DESIGN_REQUEST"),
        "raw_customer_text": tool_input["raw_customer_text"],
        "needs_clarification": tool_input.get("needs_clarification", False),
        "clarification_questions": (
            [tool_input["clarification_question"]]
            if tool_input.get("clarification_question")
            else []
        ),
        "confidence": tool_input.get("confidence", 1.0),
        "clarity_score": tool_input.get("clarity_score", 1.0),
    }
    return Story(**story_data)


class ConversationAgent:
    """Extracts a Story from customer input using Claude tool_use."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider
        self._system_prompt = _load_system_prompt()
        self._prompt_ver = _prompt_version(self._system_prompt)

    @property
    def prompt_version(self) -> str:
        return self._prompt_ver

    async def extract_story(
        self,
        new_input: str,
        prior_turns: list[ConversationTurn] | None = None,
    ) -> tuple[Story, dict[str, Any]]:
        """Extract structured Story from customer input.

        Returns:
            (Story, metadata) where metadata contains token counts,
            model name, and prompt_version for agent_logs persistence.

        Raises:
            ValidationError: Claude returned a tool call that fails Story validation.
            Exception: Provider-level errors (rate limit, network, etc.).
        """
        messages = _build_messages(new_input, prior_turns or [])

        response = await self._provider.create_message(
            system=self._system_prompt,
            messages=messages,
            tools=[_SUBMIT_STORY_TOOL],
            tool_choice="submit_story",
            max_tokens=1024,
        )

        logger.info(
            "conversation_agent_response",
            tool=response.tool_name,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model=response.model,
            prompt_version=self._prompt_ver,
        )

        try:
            story = _parse_story(response.tool_input, new_input)
        except ValidationError as exc:
            logger.error(
                "story_validation_failed",
                errors=exc.errors(),
                raw_tool_input=response.tool_input,
            )
            raise

        metadata: dict[str, Any] = {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "model_used": response.model,
            "prompt_version": self._prompt_ver,
        }
        return story, metadata
