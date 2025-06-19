# Timing & Logging

## Purpose
Record execution times of long running external operations for debugging and performance tuning.

## Usage
- Timings are collected only for expensive external calls such as speech recognition, text generation and text to speech.
- Call `record_timing(name, start)` with a `time.time()` start timestamp when one of these operations finishes.
- Launch the assistant with `--export-timings` to persist timings to `timings.json` on shutdown.

## Internals
- Uses a global in-memory list `timings` stored in `utils/timing_logger.py`.
- Each entry contains the functionality name, start and end timestamps, and the duration in milliseconds.
- `export_timings()` writes the list to a JSON file.
- Only the LLM request/response, ElevenLabs TTS generation **and** playback (recorded separately), and Whisper transcription functions invoke `record_timing`.

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
