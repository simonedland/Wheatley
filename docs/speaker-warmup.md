# Speaker Warmup

## Purpose
Keep the speakers and audio driver active so text-to-speech playback starts immediately.

## Usage
The feature is automatically enabled when `TextToSpeechEngine` is instantiated. A background thread
plays a barely audible tone every half second to prevent the audio device from sleeping. Call
`close()` on the engine to release the hardware when shutting down.

## Internals
- The engine opens a persistent PyAudio stream at 22.05 kHz mono.
- `_keep_audio_device_alive` runs in a daemon thread, writing a -50 dB 60 Hz tone whenever
  TTS is idle.
- During playback `generate_and_play_advanced` sets a flag so the keep-alive tone pauses.

## Examples
```python
from tts.tts_engine import TextToSpeechEngine
engine = TextToSpeechEngine()
engine.generate_and_play_advanced("Ready to speak with no delay")
engine.close()
```
