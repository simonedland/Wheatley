"""Tests for the Wheatley V2 conversation manager."""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from wheatley_V2.conversation import ConversationManager


def test_construction_sets_system_and_memory_slots():
    cm = ConversationManager("you are wheatley")
    assert cm.messages[0] == {"role": "system", "content": "you are wheatley"}
    assert cm.messages[1] == {"role": "system", "content": ""}
    assert len(cm.messages) == 2
    assert cm.max_memory == 10


def test_add_appends_turns():
    cm = ConversationManager("sys")
    cm.add("user", "hello")
    cm.add("assistant", "hi there")
    assert cm.messages[2] == {"role": "user", "content": "hello"}
    assert cm.messages[3] == {"role": "assistant", "content": "hi there"}
    assert len(cm.messages) == 4


def test_add_trims_to_max_memory():
    cm = ConversationManager("sys", max_memory=3)
    for i in range(10):
        cm.add("user", f"msg {i}")
    # Two system slots + max_memory turns.
    assert len(cm.messages) == 5
    # Oldest turns popped from index 2; only the last three kept.
    kept = [m["content"] for m in cm.messages[2:]]
    assert kept == ["msg 7", "msg 8", "msg 9"]
    # System slots untouched.
    assert cm.messages[0]["content"] == "sys"
    assert cm.messages[1]["content"] == ""


def test_update_memory_updates_slot_one_only():
    cm = ConversationManager("sys")
    cm.add("user", "hello")
    cm.update_memory("remembered fact")
    assert cm.messages[1] == {"role": "system", "content": "remembered fact"}
    # Slot 0 and the user turn are undisturbed.
    assert cm.messages[0]["content"] == "sys"
    assert cm.messages[2] == {"role": "user", "content": "hello"}
    # Replacing again overwrites rather than appends.
    cm.update_memory("new fact")
    assert cm.messages[1]["content"] == "new fact"
    assert cm.messages[2] == {"role": "user", "content": "hello"}


def test_set_system_swaps_slot_zero():
    cm = ConversationManager("old persona")
    cm.update_memory("mem")
    cm.set_system("new persona")
    assert cm.messages[0] == {"role": "system", "content": "new persona"}
    # Memory slot is unaffected.
    assert cm.messages[1]["content"] == "mem"


def test_get_returns_full_list():
    cm = ConversationManager("sys")
    cm.add("user", "hi")
    assert cm.get() is cm.messages
    assert cm.get() == [
        {"role": "system", "content": "sys"},
        {"role": "system", "content": ""},
        {"role": "user", "content": "hi"},
    ]


def test_render_substitutes_placeholders():
    from datetime import datetime

    rendered = ConversationManager.render("It is <current_time> on <current_day>.")
    assert "<current_time>" not in rendered
    assert "<current_day>" not in rendered
    # The current weekday name should appear.
    assert datetime.now().strftime("%A") in rendered


def test_render_leaves_text_without_placeholders():
    assert ConversationManager.render("plain text") == "plain text"
