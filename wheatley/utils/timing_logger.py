"""Utility for capturing execution timings across the application."""

from __future__ import annotations

import time
import datetime as _dt
import json
import os
import threading
import logging
from contextlib import contextmanager, asynccontextmanager
from typing import List, Dict, Any

# Central in-memory store for timing entries

timings: List[Dict[str, Any]] = []
# Lock to ensure thread-safe writes to the timings list
_timings_lock = threading.Lock()
_log = logging.getLogger(__name__)


def clear_timings(path: str = "timings.json") -> None:
    """Reset stored timings and remove the timing file if present.

    Parameters
    ----------
    path:
        Location of the timings JSON file to delete.
    """
    with _timings_lock:
        timings.clear()
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError as e:
            print(f"Failed to remove {path}: {e}")


def record_timing(name: str, start: float) -> None:
    """Record a timing entry.

    Parameters
    ----------
    name:
        Descriptive label for the timed operation.
    start:
        Timestamp returned by ``time.time()`` marking the beginning of
        the operation.
    """
    end = time.time()
    entry = {
        "functionality": name,
        "startTime": _dt.datetime.utcfromtimestamp(start).isoformat(),
        "endTime": _dt.datetime.utcfromtimestamp(end).isoformat(),
        "durationMs": int((end - start) * 1000),
        "thread": threading.current_thread().name,
    }
    with _timings_lock:
        timings.append(entry)
    _log.info("Timing %s took %sms", name, entry["durationMs"])


@contextmanager
def time_block(name: str):
    """Context manager to time a code block and record the duration."""
    start = time.time()
    try:
        yield
    finally:
        record_timing(name, start)


@asynccontextmanager
async def async_time_block(name: str):
    """Async context manager variant of :func:`time_block`."""
    start = time.time()
    try:
        yield
    finally:
        record_timing(name, start)


def export_timings(path: str = "timings.json") -> None:
    """Write accumulated timings to ``path`` in JSON format."""
    print(f"Exporting timings to {path}...")
    with _timings_lock:
        data = sorted(timings, key=lambda x: x["startTime"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
