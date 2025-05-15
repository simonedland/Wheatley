# AI Summary

### C:\GIT\eatly\Wheatley\Weatly\python\src\stt\stt_engine.py
The Python code defines a `SpeechToTextEngine` class designed to record audio, detect speech, and transcribe it into text. The class is initialized with configuration settings for audio recording, such as chunk size, format, channels, rate, and silence threshold, which are loaded from a YAML configuration file.

The `record_until_silent` method captures audio input until silence is detected. It uses the PyAudio library to open an audio stream and monitors the amplitude of the audio data. Recording starts when the amplitude exceeds a specified threshold and stops after a period of silence. The recorded audio is saved to a temporary WAV file.

The `transcribe` method uses OpenAI's Whisper model to convert the recorded audio into text by sending the audio file to the model and retrieving the transcription result.

The `record_and_transcribe` method combines these functionalities by recording audio, transcribing it, and then deleting the temporary audio file. There is also a `dry_run` method intended to simulate speech recognition using a Whisper model deployed on Azure, though it currently returns a placeholder string.
