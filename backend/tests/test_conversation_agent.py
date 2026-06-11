"""Unit tests for ConversationAgent — no API calls, uses MockProvider."""

from __future__ import annotations

import pytest

from app.agents.conversation import ConversationAgent, _build_messages, _parse_story
from app.models.schemas import ConversationTurn, KeralaTheme, Story
from app.providers.mock import MockProvider

# ---------------------------------------------------------------------------
# _build_messages
# ---------------------------------------------------------------------------

def test_build_messages_no_prior_turns():
    msgs = _build_messages("I grew up by the backwaters", [])
    assert len(msgs) == 1
    assert msgs[0].role == "user"
    assert msgs[0].content == "I grew up by the backwaters"


def test_build_messages_with_prior_turns():
    prior = [
        ConversationTurn(
            turn_number=1,
            customer_input="Tell me about my home",
            agent_text_reply="What aspect of your home do you cherish most?",
        )
    ]
    msgs = _build_messages("The smell of coconut oil on festival mornings", prior)
    assert len(msgs) == 3
    assert msgs[0].role == "user"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == "What aspect of your home do you cherish most?"
    assert msgs[2].role == "user"


def test_build_messages_prior_turn_without_reply():
    prior = [ConversationTurn(turn_number=1, customer_input="hello", agent_text_reply=None)]
    msgs = _build_messages("more detail", prior)
    assert len(msgs) == 2
    assert all(m.role == "user" for m in msgs)


# ---------------------------------------------------------------------------
# _parse_story
# ---------------------------------------------------------------------------

def test_parse_story_maps_symbols_to_keywords():
    tool_input = {
        "themes": ["backwaters"],
        "emotions": ["nostalgia"],
        "symbols": ["fishing_boat", "sunset"],
        "cultural_elements": ["Kerala backwaters"],
        "design_complexity": "medium",
        "intent": "DESIGN_REQUEST",
        "needs_clarification": False,
        "clarification_question": None,
        "raw_customer_text": "the backwaters",
        "confidence": 0.9,
        "clarity_score": 0.85,
    }
    story = _parse_story(tool_input, "the backwaters")
    assert story.keywords == ["fishing_boat", "sunset"]
    assert story.cultural_refs == ["Kerala backwaters"]
    assert story.themes == [KeralaTheme.BACKWATERS]


def test_parse_story_fills_raw_customer_text_if_missing():
    tool_input = {
        "themes": ["monsoon"],
        "emotions": ["joy"],
        "symbols": ["rain"],
        "cultural_elements": [],
        "design_complexity": "simple",
        "intent": "DESIGN_REQUEST",
        "needs_clarification": False,
        "clarification_question": None,
        "raw_customer_text": "",
        "confidence": 0.8,
        "clarity_score": 0.7,
    }
    story = _parse_story(tool_input, "Kerala rain season")
    assert story.raw_customer_text == "Kerala rain season"


def test_parse_story_clarification_question_becomes_list():
    tool_input = {
        "themes": [],
        "emotions": [],
        "symbols": [],
        "cultural_elements": [],
        "design_complexity": "simple",
        "intent": "DESIGN_REQUEST",
        "needs_clarification": True,
        "clarification_question": "Which part of Kerala do you call home?",
        "raw_customer_text": "home",
        "confidence": 0.5,
        "clarity_score": 0.3,
    }
    story = _parse_story(tool_input, "home")
    assert story.needs_clarification is True
    assert story.clarification_questions == ["Which part of Kerala do you call home?"]


# ---------------------------------------------------------------------------
# ConversationAgent with MockProvider
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_story_returns_story_and_metadata():
    provider = MockProvider()
    agent = ConversationAgent(provider=provider)

    story, meta = await agent.extract_story("I love the backwaters of Alappuzha")

    assert isinstance(story, Story)
    assert KeralaTheme.BACKWATERS in story.themes
    assert meta["model_used"] == "mock"
    assert meta["input_tokens"] == 150
    assert meta["output_tokens"] == 80
    assert "prompt_version" in meta


@pytest.mark.asyncio
async def test_extract_story_passes_full_history_to_provider():
    provider = MockProvider()
    agent = ConversationAgent(provider=provider)

    prior = [
        ConversationTurn(
            turn_number=1,
            customer_input="I love the sea",
            agent_text_reply="What does the sea mean to you?",
        )
    ]
    await agent.extract_story("My grandfather was a fisherman", prior_turns=prior)

    call = provider.calls[0]
    assert len(call["messages"]) == 3  # prior user + assistant + new user
    assert call["messages"][1].content == "What does the sea mean to you?"


@pytest.mark.asyncio
async def test_extract_story_prompt_version_is_sha1():
    provider = MockProvider()
    agent = ConversationAgent(provider=provider)
    _, meta = await agent.extract_story("test")
    # SHA-1 hex digest is exactly 40 chars
    assert len(meta["prompt_version"]) == 40


@pytest.mark.asyncio
async def test_extract_story_no_prior_turns():
    provider = MockProvider()
    agent = ConversationAgent(provider=provider)
    story, _ = await agent.extract_story("Just the Theyyam dance")
    assert isinstance(story, Story)


@pytest.mark.asyncio
async def test_mock_provider_raises_on_unknown_tool():
    provider = MockProvider(responses={})
    agent = ConversationAgent(provider=provider)
    with pytest.raises(ValueError, match="MockProvider has no canned response"):
        await agent.extract_story("test input")


@pytest.mark.asyncio
async def test_mock_provider_records_calls():
    provider = MockProvider()
    agent = ConversationAgent(provider=provider)
    await agent.extract_story("test 1")
    await agent.extract_story("test 2")
    assert len(provider.calls) == 2
    assert provider.calls[0]["tool_choice"] == "submit_story"
