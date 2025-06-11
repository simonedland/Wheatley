"""Utility for capturing execution timings across the application."""

from __future__ import annotations

import time
import datetime as _dt
import json
import asyncio
from typing import Callable, List, Dict, Any

# Central in-memory store for timing entries

timings: List[Dict[str, Any]] = []


def log_timing(name: str | None = None) -> Callable:
    """Decorator that records execution time for ``func``.

    Args:
        name: Optional name used for the ``functionality`` field. Defaults
            to the wrapped function's name.
    Returns:
        Callable: Wrapped function that logs timing information.
    """

    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                start_time = _dt.datetime.utcnow().isoformat()
                start = time.time()
                try:
                    return await func(*args, **kwargs)
                finally:
                    end_time = _dt.datetime.utcnow().isoformat()
                    duration = int((time.time() - start) * 1000)
                    timings.append({
                        "functionality": func_name,
                        "startTime": start_time,
                        "endTime": end_time,
                        "durationMs": duration,
                    })
            return async_wrapper

        def wrapper(*args, **kwargs):
            start_time = _dt.datetime.utcnow().isoformat()
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                end_time = _dt.datetime.utcnow().isoformat()
                duration = int((time.time() - start) * 1000)
                timings.append({
                    "functionality": func_name,
                    "startTime": start_time,
                    "endTime": end_time,
                    "durationMs": duration,
                })
        return wrapper

    return decorator


def export_timings(path: str = "timings.json") -> None:
    """Write accumulated timings to ``path`` in JSON format."""

    with open(path, "w", encoding="utf-8") as f:
        json.dump(timings, f, indent=2)

