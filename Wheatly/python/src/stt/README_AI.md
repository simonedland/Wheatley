# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\stt\stt_engine.py
The Python code defines a `SpeechToTextEngine` class designed to record audio, detect speech, and transcribe it into text. The class initializes by loading configuration settings from a YAML file, which specify audio parameters like chunk size, channels, rate, threshold, and silence limit.

The `record_until_silent` method captures audio input until silence is detected, using PyAudio. It monitors the amplitude of the audio signal to determine when to start and stop recording based on a predefined threshold. The recorded audio is saved as a temporary WAV file.

The `transcribe` method uses OpenAI's Whisper model to convert the recorded audio file into text. The `record_and_transcribe` method combines these functionalities: it records audio until silence is detected, transcribes the audio, and then deletes the temporary audio file. The class also includes a `dry_run` method for simulating transcription without actual processing.
