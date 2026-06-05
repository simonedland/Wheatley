"""Dry-run tests for the Wheatley V2 hardware interface.

These tests never touch real serial hardware; everything runs in dry-run mode.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from wheatley_V2.hardware import (  # noqa: E402
    ANIMATION_TOOLS,
    ANIMATIONS,
    HardwareInterface,
    dispatch,
)

EXPECTED_EMOTIONS = {
    "happy",
    "angry",
    "sad",
    "neutral",
    "excited",
    "confused",
    "surprised",
    "curious",
    "bored",
    "fearful",
    "hopeful",
    "embarrassed",
    "frustrated",
    "proud",
    "nostalgic",
    "relieved",
    "grateful",
    "shy",
    "disappointed",
    "jealous",
}


def test_dry_run_construction_does_not_open_serial() -> None:
    """A dry-run interface never opens a serial connection."""
    hw = HardwareInterface(dry_run=True)
    assert hw.dry_run is True
    assert hw._serial is None


def test_default_is_dry_run() -> None:
    """The default constructor (port='dryrun') is dry-run."""
    hw = HardwareInterface()
    assert hw.dry_run is True
    assert hw._serial is None


def test_play_animation_known_emotion() -> None:
    """Playing a known emotion succeeds in dry-run mode."""
    hw = HardwareInterface(dry_run=True)
    hw.play_animation("happy")  # should not raise


def test_play_animation_unknown_emotion_handled_gracefully() -> None:
    """An unknown emotion falls back to neutral without raising."""
    hw = HardwareInterface(dry_run=True)
    hw.play_animation("does_not_exist")  # should not raise


def test_set_led() -> None:
    """Setting an LED color works in dry-run mode."""
    hw = HardwareInterface(dry_run=True)
    hw.set_led((255, 128, 0))  # should not raise


def test_close_on_dry_run() -> None:
    """Closing a dry-run interface is a no-op and does not raise."""
    hw = HardwareInterface(dry_run=True)
    hw.close()


def test_dispatch_set_animation_returns_string_and_plays(monkeypatch) -> None:
    """dispatch('set_animation', ...) returns a string and calls play_animation."""
    hw = HardwareInterface(dry_run=True)
    calls: list[str] = []
    monkeypatch.setattr(hw, "play_animation", lambda emotion: calls.append(emotion))

    result = dispatch("set_animation", {"animation": "angry"}, hw=hw)

    assert isinstance(result, str)
    assert calls == ["angry"]


def test_dispatch_unknown_name_returns_none() -> None:
    """dispatch returns None for tool names this unit does not own."""
    hw = HardwareInterface(dry_run=True)
    assert dispatch("get_weather", {"city": "Oslo"}, hw=hw) is None


def test_animations_contains_all_expected_emotions() -> None:
    """ANIMATIONS contains exactly the expected emotion set."""
    assert set(ANIMATIONS.keys()) == EXPECTED_EMOTIONS


def test_schema_enum_matches_animations_keys() -> None:
    """The tool schema enum matches the ANIMATIONS keys."""
    tool = ANIMATION_TOOLS[0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "set_animation"
    enum = tool["function"]["parameters"]["properties"]["animation"]["enum"]
    assert set(enum) == set(ANIMATIONS.keys())


def test_animation_table_shapes_are_consistent() -> None:
    """Every emotion has ten entries per per-servo list and a 3-channel color."""
    for emotion, params in ANIMATIONS.items():
        for key in ("velocities", "target_factors", "idle_ranges", "intervals"):
            assert len(params[key]) == 10, f"{emotion}.{key} wrong length"
        assert len(params["color"]) == 3, f"{emotion}.color wrong length"
