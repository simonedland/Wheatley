# AI Codebase Overview

The provided Python scripts are part of a larger project named "Wheatly," which appears to be a voice-activated AI assistant integrated with hardware components. Here's a detailed breakdown of each script's purpose and functionality:

### `ad_nauseam.py`
This script generates AI-based summaries for Python and Arduino source files using the OpenAI API. It excludes virtual environment directories and organizes summaries into `README_AI.md` files. Key components include configuration management, an LLM client for API interactions, a directory crawler for file discovery, and a summarization orchestrator.

### `install_prerequisites.py`
Automates the installation of Python packages from a `requirements.txt` file, providing a progress bar for user feedback. It constructs the file path, checks for its existence, reads package names, and installs them using `subprocess`.

### `old_inspiration.py`
A utility script for voice interactions, hotword detection, and time measurement. It records audio, detects hotwords using Porcupine, and transcribes audio with OpenAI's Whisper model. It also includes a timer class for measuring code execution time.

### `M5Stack_Core2.ino`
An Arduino sketch for controlling a 7-servo robotic head with a touch UI on the M5Stack Core-2. It communicates with an OpenRB-150 board via UART2 and manages a NeoPixel LED strip for visual feedback. It includes a demo mode and handles servo and LED commands.

### `OpenRB-150.ino`
Facilitates communication between a computer and Dynamixel motors using an Arduino board. It acts as a bridge for data transfer between USB and the Dynamixel bus, handling serial communication and LED status indication.

### `main.py`
The main entry point for the Wheatley assistant, integrating speech-to-text, text-to-speech, an LLM client, and an Arduino interface. It uses an asynchronous event loop to manage user interactions and hardware control, leveraging APIs for AI-driven conversations.

### `puppet.py`
A GUI application for controlling servos connected to an OpenRB-150/Core-2 system. It provides real-time feedback on servo positions and allows users to configure and move servos through a user-friendly interface, supporting preset management.

### `test.py`
A unit testing script for the assistant application, validating configuration loading, assistant initialization, conversation management, and interactions with language models and speech engines using the `unittest` framework.

### `assistant.py`
Manages conversation history for the Wheatley assistant, maintaining a bounded history buffer with dynamic updates to the system message. It ensures controlled memory usage and provides a structured way to manage interactions.

### `arduino_interface.py`
Controls Arduino-based servo hardware, managing servo animations and LED indicators based on emotions. It includes classes for interfacing with the Arduino and controlling multiple servos, supporting emotion-based animations.

### `google_agent.py`
Integrates with Google Calendar to fetch and display events, using a language model to decide on calendar-related actions. It handles authentication and configuration loading, providing a framework for calendar management.

### `llm_client.py`
A client wrapper for various APIs, enabling tasks like text-to-speech, chat interactions, and workflow execution. It integrates with Google Calendar, Spotify, and weather services, using OpenAI for decision-making.

### `llm_client_utils.py`
Provides utility functions and tool definitions for the LLM client, facilitating tasks like fetching jokes, quotes, and city coordinates. It defines tools for dynamic use by the LLM client.

### `spotify_agent.py`
Interacts with Spotify's API to manage music-related tasks, using OpenAI to interpret user requests. It provides a command-line interface for searching tracks, managing playback, and more.

### `spotify_ha_utils.py`
A utility for Spotify API interaction, focusing on queue and playback management. It offers a CLI with optional pretty-printing, supporting track search, queue management, and playback control.

### `stt_engine.py`
Provides speech-to-text conversion with hotword detection, using external APIs and hardware interfaces. It manages audio recording, transcription, and asynchronous hotword listening.

### `tts_engine.py`
Converts text to speech using the ElevenLabs API, handling configuration, API interaction, and audio playback. It manages temporary files for audio storage and includes error handling for robustness.

Overall, these scripts collectively form a sophisticated AI assistant capable of voice interaction, hardware control, and integration with external services. They leverage various APIs and libraries to provide a comprehensive user experience.