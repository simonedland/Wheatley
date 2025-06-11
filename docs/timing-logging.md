# Timing & Logging

## Purpose
Record execution times of key functionalities for debugging and performance tuning.

## Usage
- Decorate functions with `log_timing()` to automatically capture timing data.
- Launch the assistant with `--export-timings` to persist timings to `timings.json` on shutdown.

## Internals
- Uses a global in-memory list `timings` stored in `utils/timing_logger.py`.
- Each entry contains the functionality name, start and end timestamps, and the duration in milliseconds.
- `export_timings()` writes the list to a JSON file.

## Examples
```python
from utils.timing_logger import log_timing, export_timings

@log_timing("heavy_task")
def heavy_task():
    ...

export_timings()  # writes timings.json
```
