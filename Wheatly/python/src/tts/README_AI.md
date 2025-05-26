# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\tts\tts_engine.py
The Python code defines a `TextToSpeechEngine` class that utilizes the ElevenLabs API to convert text to speech. It reads configuration settings from a YAML file, including API keys and text-to-speech parameters like voice ID, stability, and output format. The class includes methods to generate audio from text and play it.

1. **Initialization**: The constructor reads a configuration file to set up API keys and TTS parameters. It also configures logging to suppress verbose output from the ElevenLabs library.

2. **Audio Generation**: The `elevenlabs_generate_audio` method uses the ElevenLabs API to convert text into audio chunks based on the configured settings.

3. **Audio Playback**: The `generate_and_play_advanced` method saves the generated audio to a temporary file, plays it using the `playsound` library, and then deletes the file. It handles exceptions during playback and file deletion.

4. **Execution**: When run as a script, it creates an instance of `TextToSpeechEngine` and tests the functionality by generating and playing a sample text.
