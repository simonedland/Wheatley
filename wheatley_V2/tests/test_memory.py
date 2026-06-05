"""Tests for the Wheatley V2 long-term memory module."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from wheatley_V2 import memory  # noqa: E402


def test_read_missing_returns_empty(tmp_path):
    path = str(tmp_path / "mem.json")
    assert memory.read_memory(path) == []


def test_read_ignores_non_list(tmp_path):
    path = tmp_path / "mem.json"
    path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    assert memory.read_memory(str(path)) == []


def test_overwrite_and_read_roundtrip(tmp_path):
    path = str(tmp_path / "mem.json")
    memory.overwrite_memory({"fact": "user likes cake"}, path)
    data = memory.read_memory(path)
    assert data == [{"fact": "user likes cake"}]


def test_overwrite_replaces_existing(tmp_path):
    path = str(tmp_path / "mem.json")
    memory.overwrite_memory({"a": 1}, path)
    memory.overwrite_memory({"b": 2}, path)
    assert memory.read_memory(path) == [{"b": 2}]


def test_edit_replaces_existing_index(tmp_path):
    path = str(tmp_path / "mem.json")
    memory.edit_memory(0, {"x": 1}, path)
    memory.edit_memory(1, {"y": 2}, path)
    ok = memory.edit_memory(0, {"x": 99}, path)
    assert ok is True
    assert memory.read_memory(path) == [{"x": 99}, {"y": 2}]


def test_edit_appends_when_index_out_of_range(tmp_path):
    path = str(tmp_path / "mem.json")
    memory.edit_memory(0, {"a": 1}, path)
    ok = memory.edit_memory(50, {"b": 2}, path)
    assert ok is True
    assert memory.read_memory(path) == [{"a": 1}, {"b": 2}]


def test_compress_entry_truncates_long_strings():
    long_value = "x" * 500
    result = memory._compress_entry({"k": long_value}, max_len=200)
    assert len(result["k"]) == 200
    assert result["k"].endswith("...")
    assert result["k"][:197] == "x" * 197


def test_compress_entry_keeps_short_and_nonstring():
    entry = {"short": "hi", "num": 5, "list": [1, 2, 3]}
    result = memory._compress_entry(entry)
    assert result == entry
    assert result is not entry  # returns a copy


def test_optimize_memory_caps_at_100():
    data = [{"i": i} for i in range(150)]
    optimized = memory._optimize_memory(data)
    assert len(optimized) == 100
    assert optimized[0] == {"i": 50}
    assert optimized[-1] == {"i": 149}


def test_optimize_memory_keeps_small_lists_unchanged():
    data = [{"i": i} for i in range(10)]
    assert memory._optimize_memory(data) == data


def test_edit_compresses_long_strings(tmp_path):
    path = str(tmp_path / "mem.json")
    memory.edit_memory(0, {"k": "y" * 500}, path)
    stored = memory.read_memory(path)
    assert len(stored[0]["k"]) == 200
    assert stored[0]["k"].endswith("...")


def test_as_context_formats_correctly(tmp_path):
    path = str(tmp_path / "mem.json")
    memory.edit_memory(0, {"a": 1}, path)
    memory.edit_memory(1, {"b": 2}, path)
    ctx = memory.as_context(path)
    expected = (
        "LONG TERM MEMORY:\n" + json.dumps({"a": 1}) + "\n" + json.dumps({"b": 2})
    )
    assert ctx == expected


def test_as_context_empty(tmp_path):
    path = str(tmp_path / "mem.json")
    assert memory.as_context(path) == "LONG TERM MEMORY:\n"


def test_dispatch_write(tmp_path, monkeypatch):
    path = str(tmp_path / "mem.json")
    monkeypatch.setattr(memory, "MEMORY_FILE", path)
    result = memory.dispatch("write_long_term_memory", {"data": {"fact": "hi"}})
    assert isinstance(result, str)
    assert memory.read_memory(path) == [{"fact": "hi"}]


def test_dispatch_edit(tmp_path, monkeypatch):
    path = str(tmp_path / "mem.json")
    monkeypatch.setattr(memory, "MEMORY_FILE", path)
    memory.dispatch("write_long_term_memory", {"data": {"a": 1}})
    result = memory.dispatch("edit_long_term_memory", {"index": 0, "data": {"a": 2}})
    assert isinstance(result, str)
    assert "0" in result
    assert memory.read_memory(path) == [{"a": 2}]


def test_dispatch_unknown_returns_none():
    assert memory.dispatch("some_other_tool", {"foo": "bar"}) is None


def test_memory_tools_well_formed():
    names = set()
    for tool in memory.MEMORY_TOOLS:
        assert tool["type"] == "function"
        assert "function" in tool
        assert "name" in tool["function"]
        assert "parameters" in tool["function"]
        names.add(tool["function"]["name"])
    assert names == {"write_long_term_memory", "edit_long_term_memory"}
