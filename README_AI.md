# AI Codebase Overview

The provided Python scripts are part of a project designed to facilitate AI-based summarization, package installation, voice interaction, and hardware control. Here's a summary of each script's purpose and logic:

1. **ad_nauseam.py**: This script generates AI-based summaries for Python and Arduino files using the OpenAI API. It configures settings from a YAML file, scans directories for relevant files, and excludes virtual environments. The summaries are written to `README_AI.md` files, with an overview summary for the entire codebase. A CLI allows users to specify directories and options like dry runs and verbosity.

2. **install_prerequisites.py**: Automates the installation of packages listed in a `requirements.txt` file. It verifies the file's existence, reads package names, and installs them using `pip`, displaying a progress bar. Errors are handled with messages, and a success message is printed upon completion.

3. **old_inspiration.py**: Integrates voice interaction, weather retrieval, and hotword detection. It fetches weather data, records and transcribes audio, and listens for hotwords using the Porcupine library. It includes utility classes for timing and integrates with Google Calendar and Arduino devices.

4. **test.ino (M5 stack Core2)**: Controls servos using an M5Stack device, providing a user interface for adjusting servo states. Users can modify servo angles and velocities via the device's screen or serial commands. It supports idle movements for natural motion simulation.

5. **default.ino (OpenRB150)**: Facilitates communication between a computer and a Dynamixel servo motor. It transmits data between USB and the servo, with an LED indicating data activity.

6. **test_calibration.ino (OpenRB150)**: Calibrates the range of motion for DYNAMIXEL servos, finding mechanical limits by moving the servo until it stalls. It defaults to a ±30° range if no stall is detected.

7. **main.py**: Creates an AI assistant for speech and text interaction, integrating STT, TTS, and GPT for conversation management. It interfaces with Arduino for animations and servo control, providing a conversational experience with visual and auditory feedback.

8. **test.py**: A suite of unit tests for the conversational AI system, verifying configuration loading, assistant initialization, conversation handling, LLM functionality, and TTS operations.

9. **assistant.py**: Manages conversation history with a fixed memory size, loading a system message from a YAML file. It maintains a list of messages and provides methods for adding, retrieving, and printing conversations.

10. **arduino_interface.py**: Interfaces with Arduino hardware for servo control, managing animations based on emotions. It includes classes for connection management and servo control, supporting expressive movements.

11. **google_agent.py**: Manages Google Calendar events, using an LLM to decide actions based on user input. It interacts with Google APIs to list calendars and fetch events, with placeholders for creating and deleting events.

12. **llm_client.py**: Interacts with APIs for TTS, weather retrieval, and Google Calendar management. It includes a TTS class using ElevenLabs, a GPT client for text generation, and functions for executing workflows based on input.

13. **stt_engine.py**: Records audio, detects speech, and transcribes it using OpenAI's Whisper model. It captures audio until silence is detected, saves it temporarily, and transcribes it into text.

14. **tts_engine.py**: A TTS engine using the ElevenLabs API, generating audio from text input and playing it using `playsound`. It manages temporary files and logging levels.

Overall, these scripts provide a comprehensive system for AI-driven summarization, voice interaction, and hardware control, integrating various APIs and libraries for enhanced functionality.