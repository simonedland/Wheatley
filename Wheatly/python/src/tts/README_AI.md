# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\tts\tts_engine.py
The script is a Python module designed to convert text to speech using the ElevenLabs Text-to-Speech (TTS) API and play the resulting audio. It provides a simple interface for integration into larger projects.

### Overall Purpose

The primary goal of this script is to facilitate text-to-speech conversion by interfacing with the ElevenLabs API. It handles configuration, API interaction, audio generation, and playback.

### Main Components

#### 1. **TextToSpeechEngine Class**

- **Initialization (`__init__` method):**
  - Loads configuration settings from a YAML file located at `config/config.yaml`.
  - Extracts TTS parameters such as `voice_id`, `stability`, `similarity_boost`, `style`, `use_speaker_boost`, `speed`, `model_id`, and `output_format`.
  - Initializes an ElevenLabs API client using an API key from the configuration.
  - Configures logging to suppress verbose output from the ElevenLabs library.

- **`elevenlabs_generate_audio` Method:**
  - Interacts with the ElevenLabs API to convert text into audio chunks using specified voice settings.
  - Returns a generator that yields these audio chunks.

- **`generate_and_play_advanced` Method:**
  - Uses the `elevenlabs_generate_audio` method to generate audio for the given text.
  - Writes the audio chunks to a temporary MP3 file.
  - Plays the audio file using the `playsound` library.
  - Ensures the temporary file is deleted after playback, handling any exceptions that may occur during playback or file deletion.

### Structure and Interaction

- The script is structured around the `TextToSpeechEngine` class, which encapsulates all functionality related to text-to-speech conversion and playback.
- Configuration is loaded once during initialization to minimize runtime overhead.
- The class methods interact with the ElevenLabs API to perform the conversion and use the `playsound` library for audio playback.
- Temporary files are used for audio storage to ensure they are automatically managed by the operating system.

### External Dependencies

- **ElevenLabs API:** Used for text-to-speech conversion.
- **playsound Library:** Used for playing audio files.
- **PyYAML Library:** Used for parsing the YAML configuration file.
- **Logging Module:** Used for logging errors and suppressing verbose output.

### Configuration Requirements

- A configuration file (`config/config.yaml`) is required, containing:
  - API key for ElevenLabs.
  - TTS parameters such as `voice_id`, `stability`, `similarity_boost`, etc.

### Notable Logic

- **Temporary File Management:** The script uses Python's `NamedTemporaryFile` to handle audio files, ensuring they are automatically cleaned up after use.
- **Error Handling:** The script includes error handling for both audio playback and file deletion to ensure robustness.

### Execution

- When run directly, the script performs a basic test by converting and playing the text "Hello, world! This is a test." using the `TextToSpeechEngine`.
