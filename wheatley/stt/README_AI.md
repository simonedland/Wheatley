# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\stt\stt_engine.py
Certainly! Here is a **detailed summary and analysis** of the provided Python script:

---

## **Overall Purpose**

The script implements a **speech-to-text (STT) utility** with **hotword detection** and optional hardware integration (e.g., LED signaling via Arduino). Its main goal is to enable hands-free voice input by:

- Listening for a configurable hotword (wake word) using the **Porcupine** engine.
- Recording speech after the hotword is detected.
- Transcribing the recorded speech using **OpenAI Whisper**.
- Providing visual feedback (LED colors) about the microphone state.
- Supporting both synchronous and asynchronous (background) operation.

---

## **Main Class: `SpeechToTextEngine`**

This is the core class encapsulating all STT and hotword logic. Its responsibilities include:

### **Initialization (`__init__`)**

- Loads configuration from a YAML file (`config/config.yaml`), including STT settings and API keys.
- Sets up audio parameters (chunk size, sample rate, channels, etc.).
- Initializes hardware integration (Arduino interface for LED control).
- Calibrates the microphone's speech/ambient noise threshold.
- Sets up OpenAI API key for Whisper transcription.

### **LED State Management**

- Uses predefined RGB color constants to indicate microphone states (listening, recording, processing, paused).
- Updates the hardware LED via the Arduino interface (if present).

### **Microphone Threshold Calibration**

- Measures ambient noise and spoken audio to set a dynamic threshold for speech detection.
- Uses LED blinking to prompt the user for calibration phases (ambient, then speech).

### **Listening Control**

- Methods to **pause**, **resume**, and **check** listening state.
- Updates LED to reflect paused state.

### **Audio Stream Handling**

- Connects to the microphone input, trying different device indices for robustness.
- Cleans up audio streams and resources on shutdown.

### **Recording Logic**

- **`record_until_silent`**: Records audio when sound above the threshold is detected, stops after a period of silence.
- Saves the captured audio to a temporary WAV file for later transcription.
- Tracks and prints amplitude statistics for debugging.

### **Transcription Logic**

- **`transcribe`**: Sends the recorded WAV file to OpenAI Whisper (via OpenAI API) and retrieves the transcribed text.
- **`record_and_transcribe`**: Combines recording and transcription into a single step.

### **Hotword Detection**

- **`hotword_config`**: Configures the Porcupine hotword engine with keywords and sensitivities.
- **`listen_for_hotword`**: Listens for a hotword (wake word) and blocks until detected, or until interrupted/paused.
- Uses Porcupine's API key (from config) and can fall back to default keywords.

### **Voice Input Workflow**

- **`get_voice_input`**: Waits for a hotword, then records and transcribes the user's speech, returning the result.
- **`hotword_listener`**: An asynchronous background task that listens for hotwords and puts transcribed results into an async queue (for integration with event-driven systems).

### **Cleanup**

- **`cleanup`**: Safely closes all audio streams, terminates PyAudio and Porcupine resources, and resets the LED.

---

## **Structure & Component Interaction**

- The class is **self-contained** and manages its own state (audio streams, thresholds, LED state, etc.).
- **External configuration** (YAML) is used for all sensitive and tunable parameters (API keys, audio settings).
- **LED feedback** is tightly integrated, providing real-time status to the user.
- **Hotword detection** and **speech recording** are sequential: the engine waits for a hotword, then records speech, then transcribes.
- **Async support** via `hotword_listener` allows integration into event loops or async applications.

---

## **External Dependencies**

- **PyAudio**: For real-time audio capture from the microphone.
- **NumPy**: For efficient audio data processing (amplitude calculations).
- **OpenAI**: For Whisper-based speech-to-text transcription.
- **pvporcupine**: For wake word (hotword) detection.
- **PyYAML**: For configuration file parsing.
- **wave**: For saving audio in WAV format.
- **struct**: For unpacking audio buffers.
- **asyncio**: For asynchronous background listening.
- **utils.timing_logger**: For timing/profiling (custom utility, not standard).
- **Arduino interface** (optional): For hardware LED control (must be provided by the user).

---

## **Configuration Requirements**

- **`config/config.yaml`** must exist and contain:
  - `stt` section with audio parameters and Porcupine API key.
  - `secrets` or top-level `openai_api_key` for OpenAI Whisper.
- **Porcupine keyword file** (e.g., `stt/wheatley.ppn`) must be available if using custom wake words.
- **Arduino interface** (optional) must provide a `set_mic_led_color(r, g, b)` method.

---

## **Notable Algorithms & Logic**

### **Threshold Calibration**

- Measures **ambient noise** and **user speech** amplitudes.
- Sets the speech detection threshold to the average of the two, improving robustness across environments.

### **Silence Detection**

- While recording, counts consecutive frames below the threshold.
- Stops recording after a configurable period of silence, ensuring the user's full utterance is captured.

### **Hotword Detection Loop**

- Continuously reads audio frames and checks for hotword triggers using Porcupine.
- Handles pausing and interruption gracefully.
- Provides periodic status updates.

### **Async Voice Input**

- Uses `asyncio` to run hotword listening and speech transcription in the background, allowing integration with async applications or GUIs.

---

## **Script Entry Point**

- When run directly, the script instantiates the engine, records and transcribes up to 5 seconds of speech, prints the result, and cleans up resources.

---

## **Summary Table**

| Component                | Purpose/Responsibility                                      |
|--------------------------|------------------------------------------------------------|
| `SpeechToTextEngine`     | Main class, manages STT, hotword, hardware, and state      |
| `__init__`               | Loads config, sets up audio, calibrates, sets API keys     |
| `_update_mic_led`        | Controls hardware LED for status feedback                  |
| `calibrate_threshold`    | Dynamically sets speech/ambient threshold                  |
| `pause/resume/is_paused` | Controls listening state                                   |
| `connect_stream`         | Robustly connects to audio input                           |
| `record_until_silent`    | Records until silence, saves to WAV                        |
| `transcribe`             | Sends audio to Whisper, returns text                       |
| `hotword_config`         | Configures Porcupine hotword engine                        |
| `listen_for_hotword`     | Blocks until hotword is detected                           |
| `get_voice_input`        | Waits for hotword, records, transcribes                    |
| `hotword_listener`       | Async background hotword/speech listener                   |
| `cleanup`                | Frees all resources, resets hardware                       |

---

## **Conclusion**

This script provides a robust, configurable, and hardware-integrated speech-to-text pipeline with hotword activation, suitable for voice assistants, smart devices, or hands-free interfaces. It leverages modern APIs (OpenAI Whisper, Porcupine), supports both sync and async operation, and is designed for extensibility and integration with custom hardware (e.g., Arduino-controlled LEDs).
