# TTS and Hotword Flow

## Audio Capture

- **Sample rate**: 16 kHz
- **Chunk size**: 1024 frames
- Pre-emphasis filters and noise thresholds are handled in software (`THRESHOLD=100`).
- Uses PyAudio with mono input and 16-bit samples.

## Hotword Detection

- Powered by Porcupine (`pvporcupine`).
- Features are MFCC-based and evaluated in real time.
- Detection threshold is set through Porcupine sensitivities (default 0.5).
- State machine: `PAUSED` → `HOTWORD_COLOR` when listening → `RECORDING_COLOR` during capture → `PROCESSING_COLOR` while transcribing.

## ASR & TTS Engines

- **ASR**: OpenAI Whisper via `openai.audio.transcriptions.create()`.
- **TTS**: ElevenLabs API (`tts_engine.py`). Parameters such as stability and speed are read from config.
- Streaming TTS chunks are written to a temporary `.mp3` and played with `playsound`.

## End-to-End Flow

```
Mic -> Hotword Listener -> Record -> Whisper -> Intent -> GPT -> TTS -> Speaker
```

1. Background task waits for the hotword using Porcupine.
2. On trigger, audio is recorded until silence.
3. The file is sent to Whisper and the resulting text goes into the conversation queue.
4. GPT generates a reply and chooses an animation.
5. TTS converts the reply to audio which is played back while the mic is paused.
6. If speech-to-text is enabled, the hotword listener resumes after playback.
