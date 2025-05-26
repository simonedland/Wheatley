# AI Codebase Overview

The Python scripts in the Wheatly project serve various purposes, primarily focusing on AI-based functionalities, hardware interaction, and automation. Here's a summary of each script's purpose and logic:

1. **ad_nauseam.py**: Generates AI-based summaries for Python and Arduino files using OpenAI's API, excluding virtual environment directories. It crawls directories, summarizes files, and compiles markdown summaries.

2. **install_prerequisites.py**: Automates the installation of Python dependencies from a `requirements.txt` file, handling errors and displaying progress.

3. **old_inspiration.py**: Implements a voice-activated assistant using audio libraries and APIs. It records audio, detects hotwords, transcribes speech, and integrates with Google Calendar.

4. **M5Stack_Core2.ino**: Arduino sketch for controlling a 7-servo robotic head via an M5Stack Core2 device, using a touch interface and UART communication with an OpenRB-150 controller.

5. **default.ino**: Arduino sketch acting as a bridge for data transfer between a computer and Dynamixel motors, using USB and serial communication.

6. **OpenRB-150.ino**: Arduino sketch for servo control and calibration via UART communication between OpenRB-150 and Core-2, managing servo positions and calibration.

7. **main.py**: Initializes and runs an AI assistant with speech-to-text, text-to-speech, and hardware interaction capabilities. It manages user interactions and executes workflows.

8. **test.py**: Unit tests for verifying the functionality of various components, including configuration loading, conversation management, and language model interactions.

9. **assistant.py**: Manages conversation history with a dynamic system message, maintaining a fixed memory size for past interactions.

10. **arduino_interface.py**: Interface for controlling Arduino-connected servos, allowing animations based on emotional states.

11. **google_agent.py**: Manages Google Calendar events using Google APIs and OpenAI's language model to automate event handling.

12. **llm_client.py**: Interacts with APIs for text-to-speech, OpenAI's GPT models, and utility functions, providing a flexible command-driven interface.

13. **spotify_agent.py**: Integrates with Spotify's API to manage music playback, using OpenAI's API to interpret user requests.

14. **spotify_ha_utils.py**: Utility for Spotify API interaction, focusing on queue and playback management, with CLI demonstration capabilities.

15. **stt_engine.py**: Records audio and transcribes it into text using OpenAI's Whisper model, handling audio streams and silence detection.

16. **tts_engine.py**: Converts text to speech using the ElevenLabs API, managing audio generation and playback.

Overall, these scripts collectively provide a comprehensive system for AI-driven interaction, hardware control, and automation, leveraging various APIs and libraries.