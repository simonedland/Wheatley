# AI Summary

### C:\GIT\eatly\Wheatley\Weatly\python\src\tts\tts_engine.py
The Python code defines a text-to-speech (TTS) engine using the ElevenLabs API. It reads configuration settings from a YAML file, including API keys and TTS parameters like voice ID, stability, and speed. The engine generates audio from text input and saves it temporarily in a "temp" directory. It then plays the audio using the `playsound` library and deletes the temporary file afterward. The code also manages logging levels to suppress verbose output from the ElevenLabs library.
