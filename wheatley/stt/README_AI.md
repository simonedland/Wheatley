# AI Summary

### C:\GIT\Wheatley\Wheatley\Wheatley\python\src\stt\stt_engine.py
Here's a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script implements a **speech-to-text (STT) utility** with **hotword (wake word) detection**, audio recording, and transcription using the OpenAI Whisper API. It is designed to run on hardware that includes a microphone and an Arduino-controlled LED for visual feedback. The script can be used as a module or run directly for manual testing.

---

## **Main Components**

### **1. LED Color Constants**

- Defines RGB tuples for different microphone states (waiting for hotword, recording, processing, paused).
- Used to update a status LED via an Arduino interface.

---

### **2. `SpeechToTextEngine` Class**

**This is the core class that encapsulates all speech-to-text and hotword detection functionality.**

#### **Initialization (`__init__`)**

- Loads configuration from a YAML file (`config/config.yaml`), including:
  - Audio parameters (chunk size, channels, sample rate, etc.)
  - OpenAI API key for transcription
  - Porcupine API key for hotword detection
- Initializes state variables, threading events, and (optionally) an Arduino interface for LED control.
- Sets the initial LED state to "paused".

#### **Internal Helpers**

- **`_update_mic_led(color)`**: Updates the microphone LED to reflect the current state, using the Arduino interface if available.

#### **Listening Control**

- **`pause_listening()`**: Pauses listening/transcription, sets events, updates state and LED.
- **`resume_listening()`**: Resumes listening if paused.
- **`is_paused()`**: Checks if the system is paused.

#### **Audio Recording and Transcription**

- **`record_until_silent(max_wait_seconds=None)`**:
  - Opens a PyAudio stream and monitors audio input.
  - Begins recording when sound above a threshold is detected.
  - Stops after a period of silence.
  - Writes the recorded audio to a temporary WAV file.
  - Returns the filename or `None` if no audio was recorded.
  - Updates LED color to indicate state.

- **`transcribe(filename)`**:
  - Sends the WAV file to OpenAI's Whisper API for transcription.
  - Returns the transcribed text.

- **`record_and_transcribe(max_wait_seconds=None)`**:
  - Combines the above two steps: records audio and returns the transcription.
  - Deletes the temporary WAV file after transcription.

#### **Hotword Detection**

- **`listen_for_hotword(access_key=None, keywords=None, sensitivities=None)`**:
  - Uses the [Picovoice Porcupine](https://picovoice.ai/platform/porcupine/) library for wake word detection.
  - Loads the Porcupine API key from config if not provided.
  - Listens for specified keywords (default: "computer", "jarvis").
  - Returns the index of the detected keyword or `None` if interrupted.
  - Updates LED color to indicate hotword listening state.

#### **Voice Input Workflow**

- **`get_voice_input()`**:
  - Waits for a hotword, then records and transcribes speech.
  - Returns the transcribed text or an empty string if nothing detected.

#### **Async Hotword Listener**

- **`hotword_listener(queue)`**:
  - Asynchronous background task for continuous hotword detection and transcription.
  - Puts transcribed text into an asyncio queue for further processing.

#### **Cleanup**

- **`cleanup()`**:
  - Closes any open audio streams, PyAudio instances, and Porcupine resources.
  - Sets the LED to "paused".

---

### **3. Script Entry Point**

- If run as a script, creates an instance of `SpeechToTextEngine`, records and transcribes up to 5 seconds of speech, prints the result, and cleans up resources.

---

## **Structure and Interactions**

- **Configuration** is loaded at initialization, providing all necessary parameters and API keys.
- **LED Feedback** is provided at each state transition (waiting, recording, processing, paused).
- **Audio Input** is handled via PyAudio, with logic to select the correct input device.
- **Hotword Detection** is performed using Porcupine, which triggers the recording/transcription process.
- **Transcription** is performed via the OpenAI Whisper API.
- **Async Support** is provided for integration into event-driven applications.
- **Cleanup** ensures all hardware and API resources are properly released.

---

## **External Dependencies**

- **PyAudio**: For audio input from the microphone.
- **NumPy**: For efficient audio data processing.
- **OpenAI Python SDK**: For Whisper transcription.
- **PyYAML**: For reading configuration files.
- **pvporcupine**: For hotword detection.
- **Asyncio**: For asynchronous event loops.
- **Struct, Wave, Time, Threading**: Standard libraries for audio and concurrency.
- **Arduino Interface**: Optional, for LED control (must implement `set_mic_led_color`).

**Configuration Requirements:**
- `config/config.yaml` must exist and contain:
  - `stt` section with audio parameters and Porcupine API key.
  - `secrets` or root-level `openai_api_key`.

---

## **Notable Algorithms and Logic**

- **Voice Activity Detection**: Uses amplitude thresholding and silence duration to determine when to start/stop recording.
- **Hotword Detection Loop**: Continuously reads audio frames and checks for wake words using Porcupine.
- **LED State Machine**: Updates hardware LED to reflect system state transitions.
- **Async Hotword Listener**: Allows background hotword detection and transcription in event-driven applications.

---

## **Summary**

This script provides a robust, hardware-integrated speech-to-text solution with hotword detection, suitable for use in voice assistants or similar applications. It is modular, configurable, and supports both synchronous and asynchronous usage. The code is designed to be hardware-aware (LED feedback), secure (API keys via config), and extensible (async support, Arduino interface).
