"""Unit tests for ``wheatley_V2.personality``."""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pytest

from wheatley_V2.personality import (
    DEFAULT_PERSONALITY,
    PERSONALITY_MODES,
    PERSONALITY_TOOLS,
    PersonalityManager,
    dispatch,
)


def _sample_personalities() -> dict:
    """Return a small, well-formed personalities mapping for tests."""
    return {
        "normal": {
            "system_message": "You are Wheatley, normal mode.",
            "tts": {
                "voice_id": "voice-normal",
                "stability": 0.5,
                "similarity_boost": 0.5,
                "style": 0,
                "use_speaker_boost": True,
                "speed": 0.9,
            },
        },
        "western": {
            "system_message": "You are Wheatley, western sheriff.",
            "tts": {
                "voice_id": "voice-western",
                "stability": 0.5,
                "similarity_boost": 0.5,
                "style": 0,
                "use_speaker_boost": True,
                "speed": 0.9,
            },
        },
        "skitsofrenic": {
            "system_message": "You are Wheatley, fractured.",
            "tts": {
                "voice_id": "voice-skit",
                "stability": 0.5,
                "similarity_boost": 0.7,
                "style": 0,
                "use_speaker_boost": True,
                "speed": 1,
            },
        },
    }


def test_list_personalities() -> None:
    """``list_personalities`` returns all configured names."""
    mgr = PersonalityManager(_sample_personalities())
    assert mgr.list_personalities() == ["normal", "western", "skitsofrenic"]


def test_default_current_is_normal() -> None:
    """The manager starts on ``normal`` by default."""
    mgr = PersonalityManager(_sample_personalities())
    assert mgr.current == "normal"


def test_custom_current() -> None:
    """An explicit, valid ``current`` is honoured."""
    mgr = PersonalityManager(_sample_personalities(), current="western")
    assert mgr.current == "western"


def test_get_personality_returns_definition() -> None:
    """``get_personality`` returns the matching definition dict."""
    mgr = PersonalityManager(_sample_personalities())
    western = mgr.get_personality("western")
    assert western["system_message"] == "You are Wheatley, western sheriff."
    assert western["tts"]["voice_id"] == "voice-western"


def test_get_personality_unknown_falls_back_to_current() -> None:
    """Unknown names fall back to the current personality."""
    mgr = PersonalityManager(_sample_personalities(), current="western")
    result = mgr.get_personality("does-not-exist")
    assert result == mgr.get_personality("western")


def test_get_personality_unknown_falls_back_to_normal() -> None:
    """When current is also missing, fall back to ``normal``."""
    # Force an unusual state: current set to a missing name post-construction.
    mgr = PersonalityManager(_sample_personalities())
    mgr._current = "ghost"  # noqa: SLF001 - exercising the fallback chain
    result = mgr.get_personality("also-missing")
    assert result == mgr._personalities[DEFAULT_PERSONALITY]


def test_initial_unknown_current_falls_back_to_normal() -> None:
    """An unknown initial ``current`` falls back to ``normal``."""
    mgr = PersonalityManager(_sample_personalities(), current="nope")
    assert mgr.current == "normal"


def test_initial_falls_back_to_first_when_no_normal() -> None:
    """When ``normal`` is absent, fall back to the first personality."""
    personalities = {
        "western": _sample_personalities()["western"],
        "skitsofrenic": _sample_personalities()["skitsofrenic"],
    }
    mgr = PersonalityManager(personalities, current="missing")
    assert mgr.current == "western"


def test_empty_personalities_raises() -> None:
    """An empty mapping is rejected."""
    with pytest.raises(ValueError):
        PersonalityManager({})


def test_switch_updates_current_and_returns_dict() -> None:
    """``switch`` updates current and returns the new definition."""
    mgr = PersonalityManager(_sample_personalities())
    result = mgr.switch("skitsofrenic")
    assert mgr.current == "skitsofrenic"
    assert result["tts"]["voice_id"] == "voice-skit"


def test_switch_unknown_raises() -> None:
    """Switching to an unknown name raises ``ValueError``."""
    mgr = PersonalityManager(_sample_personalities())
    with pytest.raises(ValueError):
        mgr.switch("bogus")


def test_dispatch_set_personality_calls_spy_and_returns_string() -> None:
    """``dispatch`` validates the mode, calls the spy, and confirms."""
    calls: list[tuple[str, dict]] = []

    def spy(mode: str, args: dict) -> None:
        calls.append((mode, args))

    result = dispatch(
        "set_personality", {"mode": "western"}, on_switch=spy
    )
    assert calls == [("western", {"mode": "western"})]
    assert isinstance(result, str)
    assert "western" in result


def test_dispatch_invalid_mode_raises() -> None:
    """An invalid mode raises before calling the spy."""
    calls: list = []

    def spy(mode: str, args: dict) -> None:
        calls.append(mode)

    with pytest.raises(ValueError):
        dispatch("set_personality", {"mode": "pirate"}, on_switch=spy)
    assert calls == []


def test_dispatch_missing_mode_raises() -> None:
    """A missing mode raises ``ValueError``."""
    def spy(mode: str, args: dict) -> None:  # pragma: no cover - never called
        raise AssertionError("spy should not be called")

    with pytest.raises(ValueError):
        dispatch("set_personality", {}, on_switch=spy)


def test_dispatch_unrelated_tool_returns_none() -> None:
    """Non-personality tool names return ``None`` and skip the spy."""
    def spy(mode: str, args: dict) -> None:  # pragma: no cover - never called
        raise AssertionError("spy should not be called")

    assert dispatch("get_weather", {"city": "x"}, on_switch=spy) is None


def test_personality_tools_schema_well_formed() -> None:
    """The exported tool schema matches the OpenAI function-tool shape."""
    assert isinstance(PERSONALITY_TOOLS, list)
    assert len(PERSONALITY_TOOLS) == 1

    tool = PERSONALITY_TOOLS[0]
    assert tool["type"] == "function"

    fn = tool["function"]
    assert fn["name"] == "set_personality"
    assert isinstance(fn["description"], str) and fn["description"]

    params = fn["parameters"]
    assert params["type"] == "object"
    assert params["required"] == ["mode"]

    mode = params["properties"]["mode"]
    assert mode["type"] == "string"
    assert mode["enum"] == ["normal", "western", "skitsofrenic"]
    assert mode["enum"] == PERSONALITY_MODES
