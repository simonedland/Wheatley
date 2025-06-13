"""Persistent JSON-based storage for the assistant."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

# Default location for the memory file
MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "long_term_memory.json")


def read_memory(path: str = MEMORY_FILE) -> List[Dict[str, Any]]:
    """Return all stored memory entries from ``path``.

    Parameters
    ----------
    path:
        File to read the JSON memory from.
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


def _compress_entry(entry: Dict[str, Any], max_len: int = 200) -> Dict[str, Any]:
    """Return a copy of ``entry`` with long string values shortened.

    Parameters
    ----------
    entry:
        Memory dictionary to compress.
    max_len:
        Maximum length for string values before truncation.
    """
    result = {}
    for key, value in entry.items():
        if isinstance(value, str) and len(value) > max_len:
            result[key] = value[: max_len - 3] + "..."
        else:
            result[key] = value
    return result


def _optimize_memory(data: List[Dict[str, Any]], max_entries: int = 100) -> List[Dict[str, Any]]:
    """Return ``data`` trimmed to ``max_entries`` most recent items."""
    if len(data) > max_entries:
        data = data[-max_entries:]
    return data


def append_memory(entry: Dict[str, Any], path: str = MEMORY_FILE) -> None:
    """Append ``entry`` to the memory file located at ``path``.

    Parameters
    ----------
    entry:
        Arbitrary JSON-serialisable dictionary to store.
    path:
        File to write the memory entry to.
    """
    data = read_memory(path)
    data.append(_compress_entry(entry))
    data = _optimize_memory(data)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to write memory to {path}: {e}")



def edit_memory(index: int, entry: Dict[str, Any], path: str = MEMORY_FILE) -> bool:
    """Replace or append a memory entry.

    If ``index`` refers to an existing item it is replaced with ``entry``.
    Otherwise ``entry`` is appended to the end of the memory list.  This
    behaviour avoids errors when the model attempts to edit a non-existent
    index.

    Parameters
    ----------
    index:
        Zero-based list position of the entry to replace.
    entry:
        New dictionary to store at the given index or to append.
    path:
        File where the long term memory is stored.

    Returns
    -------
    bool
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

