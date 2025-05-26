# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\stt\stt_engine.py
The Python code defines a class `SpeechToTextEngine` designed to record audio and transcribe it into text. Here's a summary of its purpose and logic:

1. **Initialization**: The class loads configuration settings from a YAML file, setting parameters for audio recording such as chunk size, format, channels, rate, threshold, and silence limit.

2. **Dry Run Method**: A placeholder method simulates speech recognition using a Whisper model deployed on Azure, returning a dummy text.

3. **Audio Recording**: The `record_until_silent` method captures audio input until a period of silence is detected. It uses PyAudio to handle audio streams, monitoring amplitude to determine when to start and stop recording. It saves the recorded audio to a temporary WAV file.

4. **Transcription**: The `transcribe` method sends the recorded audio file to OpenAI's Whisper model to obtain a transcription of the audio content.

5. **Combined Recording and Transcription**: The `record_and_transcribe` method integrates the recording and transcription processes, returning the transcribed text and deleting the temporary audio file after processing.
