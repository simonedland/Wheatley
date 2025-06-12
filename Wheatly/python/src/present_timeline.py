"""Utility to display a chronological timeline from timing and log files."""

from __future__ import annotations

import json
import os
import re
import datetime as dt
from typing import List, Dict


def load_timings(path: str = "timings.json") -> List[Dict[str, str]]:
    """Load timing entries from ``path`` if it exists."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_logs(path: str = "assistant.log") -> List[Dict[str, str]]:
    """Parse ``assistant.log`` into timestamped entries."""
    events = []
    if not os.path.exists(path):
        return events
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            match = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+([A-Z]+):\s+(.*)$", line)
            if match:
                ts_str, level, message = match.groups()
                ts = dt.datetime.fromisoformat(ts_str)
                events.append({"timestamp": ts, "description": f"LOG {level}: {message.strip()}"})
    return events


def present_timeline(timing_file: str = "timings.json", log_file: str = "assistant.log") -> None:
    """Print combined timing and log events sorted by time."""
    events: List[Dict[str, str]] = []
    for t in load_timings(timing_file):
        ts = dt.datetime.fromisoformat(t["startTime"])
        events.append({"timestamp": ts, "description": f"{t['functionality']} took {t['durationMs']}ms"})
    events.extend(load_logs(log_file))
    events.sort(key=lambda e: e["timestamp"])
    for event in events:
        print(f"{event['timestamp'].isoformat()} - {event['description']}")


if __name__ == "__main__":
    present_timeline()
