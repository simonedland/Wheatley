# TTS and Hotword Flow

This document provides an overview of how Wheatley handles text‑to‑speech (TTS) and hotword detection for speech‑to‑text (STT).

## Text to Speech
1. **Initialisation** – `TextToSpeechEngine` reads `config/config.yaml` for ElevenLabs settings. An API client is created once and reused.
2. **Generating Speech** – `generate_and_play_advanced(text)` converts text into MP3 chunks using the ElevenLabs API. The chunks are written to a temporary file.
3. **Playback** – The temporary MP3 file is played via `playsound`. After playback the file is deleted.

The use of `NamedTemporaryFile` keeps file operations minimal and avoids leaving stray files on disk.

## Hotword Management
1. **Listening Loop** – `SpeechToTextEngine.listen_for_hotword()` creates a Porcupine hotword detector and continuously reads audio frames.
2. **Detection** – Each audio frame is analysed for configured keywords. When a keyword is detected the function returns its index.
3. **Integration** – Higher level workflows pause listening during TTS playback and resume afterwards so that hotword detection is responsive.

Once a hotword is detected, the engine records speech until a short period of silence is reached and then submits the audio to OpenAI Whisper for transcription.

The engine exposes `pause_listening()` and `resume_listening()` helpers which are used by `main.py` when playing back responses.

