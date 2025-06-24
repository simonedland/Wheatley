# STT Threshold Calibration

## Purpose
Automatically measure ambient and speaking volume to set the speech detection threshold.

## Usage
- Runs automatically when `SpeechToTextEngine` is created if STT is enabled.
- Blinks the microphone LED blue for 5 seconds while measuring ambient noise.
- Then blinks red for 5 seconds while the user speaks.
- The resulting threshold is stored in `SpeechToTextEngine.THRESHOLD`.

## Internals
- Captures audio samples using PyAudio during both measurement phases.
- Tracks maximum amplitude for ambient and speech windows.
- The threshold is set halfway between these maxima.
- LED blinking uses `set_mic_led_color` via `_update_mic_led`.

## Examples
```python
from stt.stt_engine import SpeechToTextEngine
engine = SpeechToTextEngine()
print(engine.THRESHOLD)
```
