# Timing & Logging

## Purpose
Record execution times of key functionalities for debugging and performance tuning.

## Usage
- Call `record_timing(name, start)` with a `time.time()` start timestamp when an operation finishes.
- Launch the assistant with `--export-timings` to persist timings to `timings.json` on shutdown.

## Internals
- Uses a global in-memory list `timings` stored in `utils/timing_logger.py`.
- Each entry contains the functionality name, start and end timestamps, and the duration in milliseconds.
- `export_timings()` writes the list to a JSON file.

## Examples
```python
from utils.timing_logger import record_timing, export_timings
import time

def heavy_task():
    start = time.time()
    ...
    record_timing("heavy_task", start)

export_timings()  # writes timings.json
```
