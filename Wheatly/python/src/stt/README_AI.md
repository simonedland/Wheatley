# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\stt\stt_engine.py
### Overview

The script provides utilities for speech-to-text conversion with hotword detection capabilities. It uses external APIs and hardware interfaces to listen for specific keywords and transcribe spoken words into text. The main functionality is encapsulated in the `SpeechToTextEngine` class.

### Main Components

1. **Constants**: 
   - LED color constants (`HOTWORD_COLOR`, `RECORDING_COLOR`, `PROCESSING_COLOR`, `PAUSED_COLOR`) are defined to represent different microphone states using RGB tuples.

2. **SpeechToTextEngine Class**:
   - **Initialization**: Loads configuration from a YAML file, sets up audio parameters, and initializes OpenAI API key. It also configures the microphone LED to indicate the paused state initially.
   - **Internal Helpers**: 
     - `_update_mic_led`: Updates the LED color on the hardware to reflect the current state.
   - **Listening Control**:
     - `pause_listening`, `resume_listening`, `is_paused`: Manage the listening state, allowing the system to pause and resume listening.
   - **Audio Recording**:
     - `record_until_silent`: Records audio until silence is detected, saving it as a WAV file. It monitors amplitude to determine when to start and stop recording.
   - **Transcription**:
     - `transcribe`: Uses OpenAI's Whisper model to transcribe audio files into text.
     - `record_and_transcribe`: Combines recording and transcription into a single process.
   - **Hotword Detection**:
     - `listen_for_hotword`: Uses the Porcupine library to listen for specific keywords, indicating when a hotword is detected.
     - `get_voice_input`: Waits for a hotword, records, and transcribes the speech.
   - **Asynchronous Listening**:
     - `hotword_listener`: An asynchronous task that listens for hotwords and processes speech input in the background.
   - **Cleanup**:
     - `cleanup`: Releases resources such as audio streams and Porcupine instances.

### External Dependencies

- **pyaudio**: For handling audio input.
- **openai**: To access the Whisper transcription model.
- **yaml**: For configuration file parsing.
- **pvporcupine**: For hotword detection.
- **wave**: For handling WAV file operations.
- **numpy**: For numerical operations on audio data.
- **struct**: For unpacking audio data.
- **asyncio**: For managing asynchronous tasks.
- **threading.Event**: To manage state changes in a thread-safe manner.

### Configuration

- The script requires a `config.yaml` file containing settings for the STT engine and API keys for OpenAI and Porcupine.
- The configuration includes audio settings like chunk size, channels, rate, and thresholds for silence detection.

### Notable Logic

- **Hotword Detection**: Utilizes Porcupine's library to listen for predefined keywords. This allows the system to activate only when specific words are detected, optimizing resource usage and improving user interaction.
- **Amplitude Monitoring**: The script dynamically adjusts recording based on audio amplitude, ensuring that only relevant audio is captured.
- **Asynchronous Processing**: The `hotword_listener` function allows the system to run in the background, continuously listening for input without blocking other operations.

### Interaction

- The components interact through method calls within the `SpeechToTextEngine` class. The class manages the lifecycle of audio streams and transcription processes, ensuring resources are properly allocated and released.
- LED color updates provide visual feedback on the system's state, enhancing user experience.

### Usage

- The script can be tested manually by running it directly, which will initiate a recording and transcription process, demonstrating its capabilities.
