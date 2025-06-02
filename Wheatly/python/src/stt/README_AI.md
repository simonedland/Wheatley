# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\stt\stt_engine.py
### Overview

The script implements a speech-to-text (STT) engine using Python. Its primary purpose is to record audio, detect hotwords, and transcribe speech into text using OpenAI's Whisper model. It also includes functionality for hotword detection using the Porcupine library.

### Main Components

1. **External Dependencies**:
   - **pyaudio**: For audio recording.
   - **numpy**: For numerical operations on audio data.
   - **openai**: To interact with OpenAI's API for transcription.
   - **yaml**: For configuration file parsing.
   - **pvporcupine**: For hotword detection.
   - **wave**: For handling WAV audio files.
   - **struct**: For unpacking binary data.
   - **time**: For timing operations.

2. **Configuration**:
   - The script loads configuration settings from a YAML file located in a `config` directory. This includes audio settings, API keys, and other parameters.

3. **SpeechToTextEngine Class**:
   - **Initialization**: Loads configuration settings and initializes audio parameters. It sets up the OpenAI API key for transcription.
   
   - **Methods**:
     - **dry_run**: Simulates a transcription using a placeholder message.
     - **record_until_silent**: Records audio until silence is detected. It uses amplitude thresholds to determine when to start and stop recording. The recorded audio is saved as a WAV file.
     - **transcribe**: Sends the recorded audio to OpenAI's Whisper model for transcription and returns the transcribed text.
     - **record_and_transcribe**: Combines recording and transcription into a single method, handling file cleanup.
     - **listen_for_hotword**: Uses Porcupine to listen for specific hotwords. Returns the index of the detected hotword or `None` if interrupted.
     - **get_voice_input**: Waits for a hotword, then records and transcribes speech, returning the transcribed text.
     - **cleanup**: Cleans up audio streams and resources to prevent resource leaks.

### Structure and Interaction

- **Initialization**: The `SpeechToTextEngine` is initialized with configuration settings, including audio parameters and API keys.

- **Recording and Transcription**: The `record_until_silent` method captures audio based on amplitude thresholds. The `transcribe` method then processes this audio using OpenAI's Whisper model.

- **Hotword Detection**: The `listen_for_hotword` method uses Porcupine to listen for predefined hotwords. Upon detection, it triggers the recording and transcription process.

- **Main Execution**: If run as a standalone script, it initializes the engine and performs a test transcription, printing the result.

### Notable Logic

- **Amplitude-Based Recording**: The script uses amplitude thresholds to determine when to start and stop recording, ensuring that only relevant audio is captured.

- **Hotword Detection**: Utilizes Porcupine's efficient keyword spotting capabilities to trigger recording, allowing for hands-free operation.

- **Resource Management**: Implements a `cleanup` method to ensure that audio streams and resources are properly closed and released.

### Configuration Requirements

- **YAML Configuration File**: Must include audio settings, OpenAI API key, and Porcupine API key.
- **Audio Device Index**: The script attempts to open an audio stream with specified device indices, which may need adjustment based on the system setup.

Overall, the script provides a comprehensive solution for capturing and transcribing speech, with hotword detection for enhanced usability.
