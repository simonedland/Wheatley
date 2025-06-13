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
    data.append(entry)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to write memory to {path}: {e}")

