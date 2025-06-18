# AI Summary

### C:\GIT\Wheatley\Wheatley\Wheatley\python\src\tts\tts_engine.py
Certainly! Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script provides a simple, reusable wrapper around the [ElevenLabs Text-to-Speech (TTS) API](https://elevenlabs.io/), enabling easy conversion of text to speech and playback of the resulting audio. The script is designed to be minimal and easily integrated into larger projects, with configuration handled via an external YAML file.

---

## **Main Class: `TextToSpeechEngine`**

### **Responsibilities**

- **Configuration Management:** Loads API keys and TTS parameters from a YAML configuration file (`config/config.yaml`).
- **API Interaction:** Handles all communication with the ElevenLabs TTS API, including setting up the client and sending requests.
- **Audio Generation:** Converts input text into speech audio using the ElevenLabs API.
- **Audio Playback:** Plays back the generated audio using the `playsound` library.
- **Resource Management:** Handles temporary files for audio playback and ensures cleanup.

---

## **Key Functions and Their Roles**

### **1. `__init__`**

- **Configuration Loading:** On instantiation, the class reads the YAML config file to extract:
  - ElevenLabs API key (from the `secrets` section).
  - TTS parameters such as voice ID, model ID, output format, and voice settings (from the `tts` section).
- **API Client Initialization:** Sets up an `ElevenLabs` client instance with the API key for reuse.
- **Logging Configuration:** Reduces log noise from the underlying ElevenLabs library.

### **2. `elevenlabs_generate_audio(text)`**

- **Purpose:** Calls the ElevenLabs API to synthesize speech from the provided text.
- **Returns:** A generator yielding audio data chunks (in the specified format, e.g., MP3).
- **Parameters:** Uses the voice ID, model ID, voice settings, and output format from the configuration.

### **3. `generate_and_play_advanced(text)`**

- **Purpose:** High-level method that:
  - Generates audio for the given text.
  - Writes the audio chunks to a temporary file.
  - Plays the audio file using `playsound`.
  - Cleans up the temporary file after playback.
- **Error Handling:** Logs errors if playback or file deletion fails.

---

## **Script Structure and Component Interaction**

1. **Configuration:** On instantiation, the engine loads settings from `config/config.yaml`.
2. **Text-to-Speech Conversion:** When `generate_and_play_advanced` is called, it:
   - Uses `elevenlabs_generate_audio` to get audio chunks from the API.
   - Writes these chunks to a temporary MP3 file.
3. **Playback:** Plays the temporary audio file using the `playsound` library.
4. **Cleanup:** Deletes the temporary file after playback, handling errors gracefully.

---

## **External Dependencies**

- **`playsound`**: For cross-platform audio playback.
- **`elevenlabs`**: Official ElevenLabs Python client for TTS API interaction.
- **`pyyaml`**: For parsing the YAML configuration file.
- **Standard Libraries**: `os`, `logging`, `datetime`, `tempfile`.

---

## **APIs and Configuration Requirements**

- **ElevenLabs API Key:** Must be present in `config/config.yaml` under `secrets.elevenlabs_api_key`.
- **TTS Settings:** Voice ID, model ID, output format, and voice settings are configurable under the `tts` section of the YAML file.
- **YAML File Location:** Expects the config file at `config/config.yaml` relative to the script's parent directory.

---

## **Notable Algorithms and Logic**

- **Efficient Configuration Loading:** Loads configuration once at initialization to minimize runtime overhead.
- **Streaming Audio Handling:** Uses a generator to handle potentially large audio data in chunks, which is memory-efficient.
- **Temporary File Management:** Uses `NamedTemporaryFile` to safely handle audio files, ensuring they are cleaned up after use.
- **Error Handling:** Robust error handling for both playback and file deletion, logging any issues encountered.

---

## **Usage Example**

When run directly, the script instantiates the `TextToSpeechEngine` and synthesizes and plays back the phrase "Hello, world! This is a test."

---

## **Summary Table**

| Component                | Responsibility                                      |
|--------------------------|-----------------------------------------------------|
| `TextToSpeechEngine`     | Main class for TTS conversion and playback          |
| `__init__`               | Loads config, sets up API client and logging        |
| `elevenlabs_generate_audio` | Calls ElevenLabs API, returns audio generator     |
| `generate_and_play_advanced` | Generates audio, plays it, cleans up file        |
| `playsound`              | Plays audio files                                   |
| `elevenlabs`             | Communicates with ElevenLabs TTS API                |
| `pyyaml`                 | Loads YAML configuration                            |

---

## **Conclusion**

This script is a well-structured, minimal wrapper for ElevenLabs TTS, focusing on easy configuration, efficient audio generation, and robust playback. It is designed for reuse and integration into larger projects, with clear separation of concerns and careful resource management. Proper configuration and required dependencies are essential for its operation.
