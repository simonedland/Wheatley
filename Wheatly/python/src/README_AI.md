# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\main.py
### Overview

The Python script is designed to create a voice-activated AI assistant that interacts with users through speech and text. It integrates various components such as speech-to-text (STT), text-to-speech (TTS), and a language model (LLM) to facilitate a conversational interface. The assistant can also interact with hardware, like Arduino, for additional functionalities.

### Main Components

1. **Imports and Dependencies:**
   - **Standard Libraries:** Used for file operations, logging, timing, and asynchronous programming.
   - **Third-Party Libraries:** 
     - `yaml` for configuration management.
     - `pyaudio` for handling audio input/output.
     - `openai` for accessing the OpenAI API.
     - `playsound` for playing audio files.
     - `colorama` for colored terminal output.
     - `pvporcupine` for hotword detection.
     - `RPi.GPIO` for Raspberry Pi GPIO control (optional).
   - **Local Modules:**
     - `ArduinoInterface` for hardware interaction.
     - `ConversationManager` for managing conversation history.
     - `GPTClient` and `Functions` for LLM interaction.
     - `TextToSpeechEngine` and `SpeechToTextEngine` for TTS and STT functionalities.

2. **Global Constants:**
   - Audio settings like chunk size, format, channels, and rate.
   - Thresholds for silence detection.

3. **Helper Functions:**
   - **Logging Setup:** Configures logging to file and suppresses verbose logs from certain libraries.
   - **Configuration Loading:** Loads configuration from a YAML file.
   - **Welcome Message:** Prints an ASCII art welcome message.

4. **Assistant Initialization:**
   - Initializes components like STT, TTS, LLM, and hardware interfaces.
   - Detects available serial ports for Arduino and handles connection errors.

5. **Event Dataclass:**
   - Represents events with attributes like source, payload, metadata, and timestamp.

6. **Async Event Handling:**
   - **User Input Producer:** Captures user input asynchronously.
   - **Hotword Listener:** Listens for a hotword to trigger voice input.
   - **Conversation Loop:** Manages the conversation flow, handling user inputs, generating responses, and executing workflows.

7. **Main Function:**
   - Loads configuration and initializes components.
   - Prints feature status and welcomes the user.
   - Starts the asynchronous conversation loop.

### Structure and Interaction

- **Initialization:** The script begins by setting up logging, loading configurations, and initializing components like STT, TTS, and LLM.
- **Event Handling:** Uses an asynchronous loop to handle user inputs, both text and voice, and processes them using the LLM.
- **Workflow Execution:** The assistant can execute predefined workflows and interact with hardware components like Arduino.
- **Response Generation:** Generates responses using the LLM and optionally uses TTS to vocalize them.
- **Cleanup:** Ensures resources are cleaned up on exit, including cancelling asynchronous tasks and handling exceptions.

### External Dependencies and Configuration

- **YAML Configuration:** The script relies on a YAML file for configuration, specifying settings for STT, TTS, and LLM.
- **OpenAI API:** Requires an API key for accessing OpenAI's language model services.
- **Hardware Interaction:** Optional interaction with Arduino hardware, with provisions for dry-run mode if no hardware is connected.

### Notable Algorithms and Logic

- **Asynchronous Event Loop:** Efficiently handles user inputs and system events in a non-blocking manner.
- **Workflow Execution:** Attempts to execute workflows multiple times, handling exceptions and retries.
- **Speech and Text Integration:** Seamlessly integrates STT and TTS for a conversational experience.

Overall, the script is a comprehensive implementation of a voice-activated AI assistant, leveraging multiple technologies to provide an interactive user experience.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\test.py
This Python script is a unit testing suite designed to test various components of a larger application, likely an AI assistant system. It uses the `unittest` framework to define and run tests on different modules and functionalities. Here's a breakdown of the script:

### Overall Purpose
The script aims to verify the correct functioning of configuration loading, assistant initialization, conversation handling, and specific functionalities related to language models (LLM), text-to-speech (TTS), and conversation management.

### Main Components

1. **ColorfulTestCase Class**
   - A custom test case class that extends `unittest.TestCase`.
   - Provides methods for assertions with potential for future customization (e.g., colored output).

2. **TestConfigLoad Class**
   - Tests the configuration loading functionality from `main.py`.
   - Ensures that the configuration is not `None` and contains expected keys such as "app", "logging", "stt", etc.

3. **TestInitializationAssistant Class**
   - Tests the initialization of the assistant using `main.initialize_assistant`.
   - Verifies that the function returns seven components, each of the correct type, including `ConversationManager`, `GPTClient`, `SpeechToTextEngine`, `TextToSpeechEngine`, `ArduinoInterface`, and two booleans for STT and TTS.

4. **TestConversationLoop Class**
   - Tests the conversation loop function from `main.py`.
   - Simulates user input using `sys.stdin` redirection to test the loop's response to an "exit" command.
   - Captures and checks the output to ensure the loop prompts the user correctly.

5. **TestLLMFunctionality Class**
   - Tests the `get_text` method of the `GPTClient` class.
   - Ensures the method returns a non-empty string when given a conversation input.

6. **TestTTSFunctionality Class**
   - Tests the `generate_and_play_advanced` method of the `TextToSpeechEngine`.
   - Confirms that the method executes without leaving temporary audio files, ensuring proper cleanup.

7. **TestConversationManagerFunctionality Class**
   - Tests the `ConversationManager` class.
   - Validates the addition and retrieval of conversation entries, ensuring messages are correctly stored and retrieved.

### Structure and Interaction

- **Dependencies**: The script relies on several external modules, including `main`, `assistant.assistant`, `llm.llm_client`, `tts.tts_engine`, and `hardware.arduino_interface`. These modules provide the core functionalities being tested.
- **Configuration**: The `main.load_config()` function is critical for initializing tests with the correct settings and dependencies.
- **Testing Logic**: Each test class focuses on a specific aspect of the application, using assertions to verify expected outcomes. The tests simulate real-world usage scenarios, such as user interactions and system responses.

### Notable Algorithms and Logic

- **Input Simulation**: The `TestConversationLoop` class uses `sys.stdin` and `sys.stdout` redirection to simulate user input and capture output, allowing for automated testing of interactive components.
- **Temporary File Management**: The `TestTTSFunctionality` class checks for leftover temporary files, ensuring that the TTS engine cleans up resources properly after execution.

This script is a comprehensive test suite ensuring that the application's components work together seamlessly and handle various scenarios correctly. It emphasizes modular testing, allowing each part of the system to be verified independently.
