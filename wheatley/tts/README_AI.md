# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\tts\tts_engine.py
Certainly! Here’s a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script provides a **simple, reusable wrapper** around the [ElevenLabs Text-to-Speech (TTS) API](https://elevenlabs.io/), allowing text to be converted to speech and played back directly on the local machine. The main class, `TextToSpeechEngine`, is designed for integration into larger projects, with configuration managed via an external YAML file. The engine maintains a persistent audio playback stream for low-latency speech output and keeps the audio device active even when not speaking.

---

## **Main Class: `TextToSpeechEngine`**

### **Responsibilities**

- **Configuration:** Loads TTS and API settings from a YAML config file.
- **API Interaction:** Uses the ElevenLabs API to generate speech audio from text.
- **Audio Playback:** Plays generated audio using a persistent, low-latency audio stream.
- **Device Management:** Keeps the audio device alive with near-silent audio to minimize playback delay.
- **Resource Management:** Cleans up audio resources when done.

---

## **Key Methods and Their Responsibilities**

### 1. **`_load_config`**
- **Purpose:** Loads TTS and API settings from `config/config.yaml`.
- **What it does:**  
  - Reads the YAML config.
  - Extracts ElevenLabs API key, voice/model IDs, and voice settings (stability, similarity, style, speed, speaker boost).
  - Sets output audio format.
- **Why:** Allows runtime configuration and easy tuning of TTS parameters.

### 2. **`__init__`**
- **Purpose:** Initializes the TTS engine.
- **What it does:**  
  - Loads configuration.
  - Sets up logging (suppresses verbose ElevenLabs logs).
  - Instantiates the ElevenLabs API client.
  - Initializes a persistent PyAudio stream for playback.
  - Starts a background thread to keep the audio device alive.
- **Why:** Ensures the engine is ready for fast, repeated TTS requests.

### 3. **`reload_config`**
- **Purpose:** Reloads configuration at runtime.
- **What it does:**  
  - Calls `_load_config` to refresh settings from the YAML file.
- **Why:** Allows dynamic updates to TTS settings without restarting the application.

### 4. **`elevenlabs_generate_audio_stream`**
- **Purpose:** Requests audio from the ElevenLabs API.
- **What it does:**  
  - Calls the API to convert text to speech.
  - Returns a generator yielding MP3 audio chunks.
- **Why:** Supports streaming playback as audio is generated, reducing latency.

### 5. **`generate_and_play_advanced`**
- **Purpose:** Generates speech from text and plays it back.
- **What it does:**  
  - Reloads configuration.
  - Starts timing for performance metrics.
  - Streams audio from the API, buffering and converting MP3 chunks to PCM for playback.
  - Writes audio to the persistent PyAudio stream in small chunks for immediate playback.
  - Records timing for both generation and playback.
- **Why:** Provides efficient, low-latency speech playback suitable for interactive applications.

### 6. **`_keep_audio_device_alive`**
- **Purpose:** Prevents the audio device from sleeping.
- **What it does:**  
  - Continuously plays a very quiet 60 Hz sine wave when not actively playing speech.
  - Runs in a background thread.
- **Why:** Keeps the audio device “warm” to avoid delays when starting playback.

### 7. **`close` and `__del__`**
- **Purpose:** Cleans up resources.
- **What they do:**  
  - Stops the keep-alive thread.
  - Closes the audio stream and terminates PyAudio.
- **Why:** Prevents resource leaks and ensures clean shutdown.

---

## **Structure and Component Interaction**

- **Configuration** is loaded at initialization and can be reloaded on demand.
- **Text input** is passed to `generate_and_play_advanced`, which:
  - Streams audio from the ElevenLabs API.
  - Buffers and converts MP3 chunks to PCM using `pydub`.
  - Writes PCM data to the persistent PyAudio stream for immediate playback.
- **A background thread** keeps the audio device alive with near-silent audio when not actively playing speech.
- **Timing information** is recorded for both TTS generation and playback phases (using an external `record_timing` function).

---

## **External Dependencies**

- **PyYAML (`yaml`):** For reading the configuration file.
- **PyAudio (`pyaudio`):** For low-level audio playback.
- **pydub:** For audio format conversion (MP3 to PCM).
- **elevenlabs:** Official ElevenLabs API client for TTS.
- **utils.timing_logger.record_timing:** For performance logging (assumed to be a custom utility).
- **threading:** For running the keep-alive function in the background.
- **Other standard libraries:** `os`, `io`, `time`, `logging`.

---

## **APIs and Configuration**

- **ElevenLabs API:** Requires an API key in `config/config.yaml` under `secrets.elevenlabs_api_key`.
- **Config File (`config/config.yaml`):**
  - Contains API key, voice ID, model ID, and voice settings.
  - Allows for easy tuning and switching of voices/models.

---

## **Notable Algorithms and Logic**

- **Persistent Audio Stream:**  
  - Keeps the audio device open to minimize latency.
  - Uses a background thread to play a near-silent tone when idle.

- **Streaming Playback:**  
  - Buffers MP3 chunks from the API and converts to PCM in small batches.
  - Begins playback as soon as enough data is buffered, rather than waiting for the full response.

- **Dynamic Buffering:**  
  - Uses different buffer sizes for initial and subsequent audio chunks to balance latency and smooth playback.

- **Performance Logging:**  
  - Records timing for both TTS generation and playback, enabling performance monitoring.

---

## **Configuration Requirements**

- **`config/config.yaml`** must exist and contain:
  - `secrets.elevenlabs_api_key`
  - `tts.voice_id`, `tts.model_id`, and other voice settings (optional, with defaults provided).

---

## **Summary**

This script is a robust, reusable TTS engine for Python projects, designed for low-latency, high-quality speech synthesis using the ElevenLabs API. It handles configuration, API interaction, audio streaming, and device management, making it easy to integrate advanced TTS capabilities into larger applications. The use of a persistent audio stream and background keep-alive thread is particularly notable for minimizing playback delays, making it suitable for interactive or real-time systems.
