# AI Codebase Overview

The provided Python scripts are part of a project named "Wheatly," which includes various functionalities ranging from AI-based code summarization to hardware interaction and conversational AI. Here's a summary of each script's purpose and logic:

1. **ad_nauseam.py**: Automates the generation of AI-based summaries for Python and Arduino files using the OpenAI API. It excludes virtual environment directories and organizes summaries into `README_AI.md` files.

2. **install_prerequisites.py**: Automates the installation of packages listed in a `requirements.txt` file, providing visual feedback on the installation progress.

3. **old_inspiration.py**: Integrates functionalities like weather retrieval, voice recording, hotword detection, and Google Calendar interaction, supporting modular voice command applications.

4. **test.ino**: An Arduino sketch for managing multiple servos with an M5Stack device, allowing manual and automated control, and displaying status on an LCD screen.

5. **default.ino**: Facilitates communication between a computer and Dynamixel motors, acting as a bridge for data transmission via USB and serial bus.

6. **test_calibration.ino**: Calibrates the range of motion for DYNAMIXEL servos, determining mechanical limits to ensure safe operation.

7. **main.py**: Initializes and runs an AI assistant that interacts through speech and text, leveraging GPT for language processing and Arduino for physical interactions.

8. **test.py**: Contains unit tests for the conversational assistant, verifying the correct behavior of components like language models and speech engines.

9. **assistant.py**: Manages conversation history with a fixed memory limit, loading system messages from a configuration file and maintaining a structured dialogue.

10. **arduino_interface.py**: Interfaces with Arduino hardware to control servos, performing animations based on emotional states, with support for a dry run mode.

11. **google_agent.py**: Manages Google Calendar events using Google APIs and OpenAI's language model, automating calendar management tasks.

12. **llm_client.py**: Interacts with APIs for tasks like text-to-speech, weather retrieval, and more, using OpenAI and ElevenLabs for processing.

13. **stt_engine.py**: Records audio, detects speech, and transcribes it into text using OpenAI's Whisper model, with functionality to handle silence detection.

14. **tts_engine.py**: Converts text to speech using the ElevenLabs API, playing the audio and managing temporary files.

Overall, the project combines AI, hardware interaction, and automation to create a comprehensive system for code summarization, conversational AI, and hardware control.