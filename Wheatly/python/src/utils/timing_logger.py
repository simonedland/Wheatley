"""Utility for capturing execution timings across the application."""

from __future__ import annotations

import time
import datetime as _dt
import json
from typing import List, Dict, Any

# Central in-memory store for timing entries

timings: List[Dict[str, Any]] = []


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
    timings.append(
        {
            "functionality": name,
            "startTime": _dt.datetime.utcfromtimestamp(start).isoformat(),
            "endTime": _dt.datetime.utcfromtimestamp(end).isoformat(),
            "durationMs": int((end - start) * 1000),
        }
    )


def export_timings(path: str = "timings.json") -> None:
    """Write accumulated timings to ``path`` in JSON format."""

    with open(path, "w", encoding="utf-8") as f:
        json.dump(timings, f, indent=2)

