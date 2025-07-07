# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\tts\tts_engine.py
Certainly! Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script provides a simple, reusable Python wrapper around the [ElevenLabs Text-to-Speech (TTS) API](https://elevenlabs.io/), allowing text to be converted to speech and played back through the system’s audio output. The main class, `TextToSpeechEngine`, handles configuration, API communication, audio stream management, and playback. It is designed for integration into larger projects, with configuration managed via a YAML file.

---

## **Main Class: `TextToSpeechEngine`**

### **Responsibilities**

- **Configuration Management:** Loads TTS and API settings from a YAML config file.
- **API Communication:** Uses the ElevenLabs API to generate speech audio from text.
- **Audio Playback:** Manages a persistent audio output stream for low-latency playback.
- **Resource Management:** Keeps the audio device alive and ensures resources are cleaned up.
- **Minimal Interface:** Exposes simple methods for generating and playing speech.

---

## **Structure and Component Interactions**

### **1. Configuration Loading**

- **Method:** `_load_config`
- **Function:** Reads `config/config.yaml` to obtain:
  - ElevenLabs API key (from a `secrets` section)
  - Voice ID, model ID, and various voice settings (from a `tts` section)
  - Output format for audio
- **Usage:** Called during initialization and can be reloaded at runtime via `reload_config`.

### **2. Initialization and Audio Stream Setup**

- **Constructor:** `__init__`
- **Functionality:**
  - Loads configuration.
  - Initializes the ElevenLabs API client.
  - Sets up a persistent PyAudio output stream (mono, 22,050 Hz, 16-bit).
  - Starts a background thread to keep the audio device alive by playing near-silent tones when not actively playing speech.

### **3. Speech Generation and Playback**

- **Method:** `elevenlabs_generate_audio_stream`
  - Calls the ElevenLabs API to generate an audio stream for a given text, yielding MP3-encoded audio chunks.
- **Method:** `generate_and_play_advanced`
  - Reloads config, starts timing, and requests an audio stream from the API.
  - Buffers incoming MP3 chunks, decodes them to PCM using `pydub`, and writes them to the persistent audio stream for immediate playback.
  - Uses initial and subsequent buffer thresholds to balance latency and smooth playback.
  - Records timing for both generation and playback phases (via `record_timing`).
- **Method:** `play_mp3_bytes`
  - Plays arbitrary MP3 audio data through the persistent stream (decoding via `pydub`).

### **4. Audio Device Keep-Alive**

- **Method:** `_keep_audio_device_alive`
  - Runs in a background thread.
  - Periodically writes a very quiet 60 Hz sine wave to the audio stream when not actively playing speech, preventing the audio device from powering down or introducing latency.

### **5. Resource Cleanup**

- **Method:** `close`
  - Stops the keep-alive thread, closes the audio stream, and terminates the PyAudio instance.
- **Destructor:** `__del__`
  - Ensures cleanup on object deletion.

---

## **External Dependencies**

- **PyYAML (`yaml`):** For reading configuration files.
- **PyAudio (`pyaudio`):** For low-level audio playback.
- **pydub:** For decoding MP3 audio and manipulating audio data.
- **elevenlabs:** Official ElevenLabs API client.
- **utils.timing_logger:** Custom module for recording timing metrics (not standard; assumed to be project-specific).
- **threading:** For background keep-alive thread.
- **io, os, time, logging:** Standard library modules.

---

## **Configuration Requirements**

- **File:** `config/config.yaml` (expected to be two directories up from the script location)
  - **`secrets.elevenlabs_api_key`:** Required for API access.
  - **`tts.voice_id`, `tts.model_id`, `tts.stability`, etc.:** Optional, with defaults provided.
- **Directory Structure:** The script expects a specific directory layout for configuration.

---

## **Notable Algorithms and Logic**

### **1. Persistent Audio Stream and Keep-Alive**

- The engine keeps the audio output stream open at all times, reducing latency for speech playback.
- A background thread writes near-silent audio when idle, preventing the audio device from sleeping or introducing pops/clicks when starting playback.

### **2. Buffered Streaming Playback**

- Audio is streamed from the ElevenLabs API in MP3 chunks.
- Chunks are buffered and periodically decoded to PCM for playback, balancing between low latency (quick start) and smooth playback (avoiding underruns).
- The buffering logic uses a larger initial buffer, then smaller chunks, to ensure playback starts quickly but remains smooth.

### **3. Timing Metrics**

- The engine records timing for both the TTS generation and playback phases, likely for performance monitoring or debugging.

---

## **How Components Interact**

- **Initialization:** Loads config, sets up API client and audio stream, starts keep-alive thread.
- **Speech Request:** On `generate_and_play_advanced`, config is reloaded, speech is requested from API, and audio is played as it streams in.
- **Playback:** Audio is decoded and written to the persistent stream; the keep-alive thread is paused during active playback.
- **Cleanup:** On close or object deletion, all resources are released.

---

## **Entry Point**

- When run as a script, it instantiates the engine and performs a test TTS playback with the phrase "Hello, world! This is a test."

---

## **Summary Table**

| Component                   | Responsibility                                        |
|-----------------------------|------------------------------------------------------|
| `TextToSpeechEngine`        | Main class for TTS and playback                      |
| `_load_config`              | Loads YAML config for API and voice settings         |
| `__init__`                  | Initializes API client, audio stream, keep-alive     |
| `reload_config`             | Reloads config at runtime                            |
| `elevenlabs_generate_audio_stream` | Streams MP3 audio from ElevenLabs API         |
| `generate_and_play_advanced`| Buffers, decodes, and plays TTS audio               |
| `play_mp3_bytes`            | Plays arbitrary MP3 data                             |
| `_keep_audio_device_alive`  | Background thread to keep audio device active        |
| `close` / `__del__`         | Cleans up resources                                 |

---

## **Conclusion**

This script provides a robust, low-latency, and easily configurable interface for ElevenLabs TTS, suitable for integration into larger Python projects. Its design emphasizes persistent audio playback, smooth streaming, and minimal configuration overhead, with careful attention to resource management and performance monitoring. External dependencies include ElevenLabs API client, PyAudio, pydub, and PyYAML, with configuration expected in a specific YAML file structure.
