"""Persistent text-based storage for the assistant."""

from __future__ import annotations

import os
from typing import List

# Default location for the memory file
MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "long_term_memory.txt")


def read_memory(path: str = MEMORY_FILE) -> List[str]:
    """Return all stored memory entries from ``path``.

    Parameters
    ----------
    path:
        File to read the memory from.
    """
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f if line.strip()]
            return lines
    except Exception:
        return []


def _compress_entry(entry: str, max_len: int = 200) -> str:
    """Return ``entry`` shortened to ``max_len`` characters.

    Parameters
    ----------
    entry:
        Memory text to compress.
    max_len:
        Maximum length for string values before truncation.
    """
    if len(entry) > max_len:
        return entry[: max_len - 3] + "..."
    return entry


def _optimize_memory(data: List[str], max_entries: int = 100) -> List[str]:
    """Return ``data`` trimmed to ``max_entries`` most recent items."""
    if len(data) > max_entries:
        data = data[-max_entries:]
    return data


def append_memory(entry: str, path: str = MEMORY_FILE) -> None:
    """Append ``entry`` to the memory file located at ``path``.

    Parameters
    ----------
    entry:
        Arbitrary text to store.
    path:
        File to write the memory entry to.
    """
    data = read_memory(path)
    data.append(_compress_entry(entry))
    data = _optimize_memory(data)
    try:
        with open(path, "w", encoding="utf-8") as f:
            for line in data:
                f.write(line + "\n")
    except Exception as e:
        print(f"Failed to write memory to {path}: {e}")


def overwrite_memory(entry: str, path: str = MEMORY_FILE) -> None:
    """Replace the entire memory with ``entry``.

    Parameters
    ----------
    entry:
        Single text string to store as the only memory item.
    path:
        File where the long term memory is stored.
    """
    data = [_compress_entry(entry)]
    data = _optimize_memory(data)
    try:
        with open(path, "w", encoding="utf-8") as f:
            for line in data:
                f.write(line + "\n")
    except Exception as e:
        print(f"Failed to write memory to {path}: {e}")



def edit_memory(index: int, entry: str, path: str = MEMORY_FILE) -> bool:
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
        New text to store at the given index or to append.
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
            for line in data:
                f.write(line + "\n")
        return True
    except Exception as e:
        print(f"Failed to write memory to {path}: {e}")
        return False

