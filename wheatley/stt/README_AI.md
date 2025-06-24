# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\stt\stt_engine.py
Certainly! Here is a **detailed summary** and analysis of the provided Python script:

---

## **Overall Purpose**

This script provides a **speech-to-text (STT) utility** with **hotword detection**. It is designed to run on hardware (optionally with an Arduino interface for LED status indication) and supports:

- **Hotword detection** (using Porcupine)
- **Audio recording** (using PyAudio)
- **Speech transcription** (using OpenAI's Whisper API)
- **Microphone state feedback** via LED colors
- **Async background listening** for voice commands

It is suitable for voice assistant applications, smart devices, or any system that needs to listen for a wake word, record speech, and transcribe it.

---

## **Main Class: `SpeechToTextEngine`**

### **Initialization and Configuration**

- **Configuration Loading**: On initialization, the class loads settings from a YAML config file (`config/config.yaml`). This includes audio parameters (chunk size, channels, sample rate), thresholds, and API keys.
- **OpenAI API Key**: The OpenAI API key is loaded from the config and set for use with Whisper.
- **LED State**: If an Arduino interface is provided, the mic LED is set to "paused" (red) at startup.

### **LED Color Constants**

- Four RGB tuples define LED colors for different mic states: waiting for hotword (blue), recording (green), processing (orange), and paused (red).

### **Internal State**

- Maintains PyAudio and Porcupine instances, audio streams, and threading events for pausing/stopping listening.

---

## **Key Methods and Their Responsibilities**

### **Microphone LED Control**

- **`_update_mic_led(color)`**: Updates the hardware LED to reflect the current microphone state.

### **Listening Control**

- **`pause_listening()`**: Pauses listening/transcription, sets LED to paused.
- **`resume_listening()`**: Resumes listening.
- **`is_paused()`**: Returns pause state.

### **Audio Recording**

- **`record_until_silent(max_wait_seconds=None)`**:
  - Opens the microphone and waits for sound above a threshold.
  - Records until a period of silence is detected or a timeout occurs.
  - Saves the recording as a WAV file.
  - Returns the filename or `None` if no audio was recorded.

### **Speech Transcription**

- **`transcribe(filename)`**:
  - Sends the WAV file to OpenAI's Whisper API for transcription.
  - Returns the transcribed text.

- **`record_and_transcribe(max_wait_seconds=None)`**:
  - Combines recording and transcription in one step.
  - Deletes the temporary audio file after transcription.

### **Hotword Detection**

- **`listen_for_hotword(access_key=None, keywords=None, sensitivities=None)`**:
  - Uses Picovoice Porcupine to listen for specified hotwords (defaults: "computer", "jarvis").
  - Loads Porcupine API key from config if not provided.
  - Returns the index of the detected keyword or `None` if interrupted.

### **Voice Input Pipeline**

- **`get_voice_input()`**:
  - Waits for a hotword.
  - Records and transcribes speech after hotword detection.
  - Returns the transcribed text.

### **Async Background Listening**

- **`hotword_listener(queue)`**:
  - Async coroutine for background listening.
  - Waits for hotword, then records and transcribes speech.
  - Puts the result into an async queue for further processing.

### **Cleanup**

- **`cleanup()`**:
  - Safely closes audio streams, terminates PyAudio and Porcupine instances, and updates the LED to "paused".

---

## **Structure and Component Interaction**

- **Config File**: Centralizes all runtime settings and secrets.
- **PyAudio**: Handles audio input for both hotword detection and speech recording.
- **Porcupine**: Provides hotword detection, either by keyword or custom model.
- **OpenAI Whisper**: Performs transcription of recorded speech.
- **Arduino Interface (optional)**: Used to provide visual feedback via LED colors.
- **Asyncio**: Enables non-blocking, background listening for voice input.

---

## **External Dependencies**

- **PyAudio**: For microphone access and audio streaming.
- **Numpy**: For efficient audio data processing.
- **OpenAI Python SDK**: For Whisper API access.
- **PyYAML**: For configuration file parsing.
- **pvporcupine**: For hotword detection.
- **Asyncio**: For async background listening.
- **Struct, Wave, Time, OS**: Standard Python modules for audio and file handling.
- **Custom Utility**: `utils.timing_logger.record_timing` for performance logging.

---

## **Configuration Requirements**

- **YAML Config File**: Must be present at `config/config.yaml` with sections for:
  - `stt` (audio settings, Porcupine API key)
  - `secrets` or `openai_api_key` (OpenAI API key)
- **Porcupine Keyword File**: If using a custom Porcupine model, must be present at `stt/wheatley.ppn`.

---

## **Notable Algorithms and Logic**

- **Voice Activity Detection**: Simple amplitude thresholding is used to detect the start and end of speech.
- **Silence Detection**: Recording stops after a configurable period of silence.
- **Hotword Detection**: Uses Porcupine's efficient keyword spotting algorithm.
- **Async Background Listening**: Allows the system to listen for voice input in a non-blocking way, suitable for integration into larger async applications.
- **LED Feedback**: Provides real-time status indication to the user via colored LEDs.

---

## **Main Script Behavior**

- If run directly, the script instantiates `SpeechToTextEngine`, records up to 5 seconds of speech, transcribes it, prints the result, and cleans up resources.

---

## **Summary Table**

| Component                | Responsibility                                          |
|--------------------------|--------------------------------------------------------|
| `SpeechToTextEngine`     | Main class for all STT, hotword, and LED logic         |
| PyAudio                  | Audio input/streaming                                  |
| Porcupine                | Hotword detection                                      |
| OpenAI Whisper           | Speech transcription                                   |
| Arduino interface        | (Optional) LED color feedback                          |
| Config file (YAML)       | Centralized settings and secrets                       |
| Asyncio                  | Background listening                                   |

---

## **Conclusion**

This script provides a robust, modular, and hardware-aware speech-to-text pipeline with hotword detection, suitable for voice assistant applications. It is configurable, supports both synchronous and asynchronous operation, and integrates with both cloud (OpenAI) and local (Porcupine) APIs. The design allows for easy extension and integration into larger systems.
