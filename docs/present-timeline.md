# Present Timeline

## Purpose
Provide a simple CLI command to view a chronological list of events after the assistant finishes running.

## Usage
- Run the assistant with timing export enabled (default behaviour).
- After shutdown execute:
  ```bash
  python present_timeline.py
  ```
  The script reads `timings.json` and `assistant.log` and prints a sorted timeline.

## Internals
- `load_timings()` parses `timings.json`.
- `load_logs()` parses `assistant.log` entries.
- `present_timeline()` merges both sources and orders them by timestamp.

## Examples
```bash
$ python present_timeline.py
2025-06-11T17:41:10.559211 - initialize_assistant took 3189ms
2025-06-11T17:41:10 INFO: some log message
...
```
