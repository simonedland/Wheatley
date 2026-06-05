"""Persistent JSON-based long-term memory for Wheatley V2.

This module ports the v1 long-term memory store into the flat ``wheatley_V2``
package and exposes a small LLM tool surface (OpenAI-format schemas plus a
``dispatch`` function) so a central router can let the model read and write
persistent memory.

The module only depends on the standard library and never imports sibling
``wheatley_V2`` modules.
"""

from __future__ import annotations

import json
import os
from typing import Any

# Default location for the memory file, relative to this module.
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "long_term_memory.json")


def read_memory(path: str = MEMORY_FILE) -> list[dict]:
    """Return all stored memory entries from ``path``.

    Args:
        path: File to read the JSON memory from.

    Returns:
        A list of memory entry dictionaries, or an empty list if the file is
        missing, unreadable, or does not contain a JSON list.
    """
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _compress_entry(entry: dict, max_len: int = 200) -> dict:
    """Return a copy of ``entry`` with long string values shortened.

    Args:
        entry: Memory dictionary to compress.
        max_len: Maximum length for string values before truncation.

    Returns:
        A new dictionary where any string value longer than ``max_len`` is
        truncated and suffixed with ``"..."``.
    """
    result: dict[str, Any] = {}
    for key, value in entry.items():
        if isinstance(value, str) and len(value) > max_len:
            result[key] = value[: max_len - 3] + "..."
        else:
            result[key] = value
    return result


def _optimize_memory(data: list[dict], max_entries: int = 100) -> list[dict]:
    """Return ``data`` trimmed to the ``max_entries`` most recent items.

    Args:
        data: Full list of memory entries.
        max_entries: Maximum number of entries to keep.

    Returns:
        The trimmed list (the last ``max_entries`` items).
    """
    if len(data) > max_entries:
        data = data[-max_entries:]
    return data


def overwrite_memory(entry: dict, path: str = MEMORY_FILE) -> None:
    """Replace the entire memory with a single ``entry``.

    Args:
        entry: Single dictionary to store as the only memory item.
        path: File where the long term memory is stored.
    """
    data = [_compress_entry(entry)]
    data = _optimize_memory(data)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to write memory to {path}: {e}")


def edit_memory(index: int, entry: dict, path: str = MEMORY_FILE) -> bool:
    """Replace or append a memory entry.

    If ``index`` refers to an existing item it is replaced with ``entry``.
    Otherwise ``entry`` is appended to the end of the memory list. This
    behaviour avoids errors when the model attempts to edit a non-existent
    index.

    Args:
        index: Zero-based list position of the entry to replace.
        entry: New dictionary to store at the given index or to append.
        path: File where the long term memory is stored.

    Returns:
        ``True`` if the entry was written successfully, ``False`` on error.
    """
    data = read_memory(path)
    if 0 <= index < len(data):
        data[index] = _compress_entry(entry)
    else:
        data.append(_compress_entry(entry))
    data = _optimize_memory(data)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Failed to write memory to {path}: {e}")
        return False


def as_context(path: str = MEMORY_FILE) -> str:
    """Return the memory serialized for injection into the conversation.

    Args:
        path: File where the long term memory is stored.

    Returns:
        A header line followed by one JSON-serialized entry per line. If there
        are no entries, only the header is returned.
    """
    entries = read_memory(path)
    return "LONG TERM MEMORY:\n" + "\n".join(json.dumps(item) for item in entries)


# ---------------------------------------------------------------------------
# LLM tool surface
# ---------------------------------------------------------------------------

MEMORY_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "write_long_term_memory",
            "description": (
                "Overwrite the long-term memory with a single entry. Use this "
                "to persist an important fact about the user or conversation "
                "across sessions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "description": "The memory entry to store.",
                    },
                },
                "required": ["data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_long_term_memory",
            "description": (
                "Edit a long-term memory entry at a given index. If the index "
                "does not exist the entry is appended instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "Zero-based index of the entry to edit.",
                    },
                    "data": {
                        "type": "object",
                        "description": "The memory entry to store at the index.",
                    },
                },
                "required": ["index", "data"],
            },
        },
    },
]


def dispatch(name: str, args: dict) -> str | None:
    """Execute a memory tool by name and return a human-readable result.

    Args:
        name: The tool name from the model's tool call.
        args: The decoded tool arguments.

    Returns:
        A short human-readable result string if ``name`` is a memory tool, or
        ``None`` if it is not (so a central router can try the next module).
    """
    if name == "write_long_term_memory":
        entry = args.get("data", {})
        overwrite_memory(entry, MEMORY_FILE)
        return "Long-term memory overwritten with new entry."
    if name == "edit_long_term_memory":
        index = args.get("index", 0)
        entry = args.get("data", {})
        ok = edit_memory(index, entry, MEMORY_FILE)
        if ok:
            return f"Long-term memory entry at index {index} updated."
        return f"Failed to update long-term memory entry at index {index}."
    return None
