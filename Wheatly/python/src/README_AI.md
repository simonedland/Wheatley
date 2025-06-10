# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\main.py
### Overview

The script serves as the main entry point for the Wheatley assistant, a voice-activated AI system that integrates speech-to-text (STT), text-to-speech (TTS), a large language model (LLM) client, and an Arduino hardware interface. It uses an asynchronous event loop to handle user interactions and control hardware components like servos and LEDs on a robot.

### Main Components

1. **Imports and Dependencies:**
   - **Standard Libraries:** Used for file operations, logging, timing, and asynchronous programming.
   - **Third-Party Libraries:** 
     - `yaml` for configuration management.
     - `openai` for accessing the OpenAI API.
     - `colorama` for colored terminal output.
     - `RPi.GPIO` for Raspberry Pi GPIO control (optional).
   - **Local Modules:**
     - `ArduinoInterface` for hardware interaction.
     - `ConversationManager` for managing conversation history.
     - `GPTClient` for LLM interactions.
     - `TextToSpeechEngine` and `SpeechToTextEngine` for TTS and STT functionalities.

2. **Logging and Configuration:**
   - Sets up robust logging to a file.
   - Loads configuration from a YAML file, which includes settings for STT, TTS, and LLM.

3. **Initialization Functions:**
   - **`initialize_assistant`:** Initializes all major components like the conversation manager, GPT client, STT and TTS engines, and Arduino interface. It also handles serial port detection for the Arduino.

4. **Event Handling:**
   - **`Event` Dataclass:** Represents events with a source, payload, metadata, and timestamp.
   - **Async Functions:** 
     - `user_input_producer` reads user input asynchronously.
     - `get_event` retrieves events from a queue.
     - `handle_non_user_event` and `process_event` manage events and update conversation history.

5. **Workflow and Interaction:**
   - **`run_tool_workflow`:** Executes tools suggested by the LLM.
   - **`generate_assistant_reply`:** Fetches a textual reply and animation from the LLM.
   - **`handle_tts_and_follow_up`:** Manages TTS output and listens for follow-up voice responses.

6. **Asynchronous Loop:**
   - **`async_conversation_loop`:** Main loop that handles user events, tool calls, and interactions with the LLM and hardware.

7. **Main Function:**
   - **`main`:** Entry point that loads configurations, initializes components, and starts the asynchronous conversation loop. It also handles initial interactions and sets up the assistant's state.

### External Dependencies and Configuration

- **OpenAI API:** Requires an API key for accessing the LLM.
- **YAML Configuration:** Contains settings for enabling/disabling STT and TTS, LLM model selection, and other application-specific configurations.
- **Arduino Interface:** Requires serial port detection and connection setup.

### Notable Logic

- **Asynchronous Event Loop:** Efficiently handles user inputs and system events in a non-blocking manner.
- **Tool Execution Workflow:** Integrates LLM suggestions to execute specific tools and update the conversation context.
- **Hardware Interaction:** Controls Arduino-based hardware components, allowing for physical responses to user interactions.

### Conclusion

The script is a comprehensive implementation of a voice-activated assistant that combines AI-driven conversation capabilities with physical hardware interaction. It leverages asynchronous programming to manage real-time user interactions and system events efficiently.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\puppet.py
### Overview

The Python script `servo_puppet.py` is a graphical user interface (GUI) application designed to control servos connected to an OpenRB-150 / Core-2 system. The application provides real-time feedback on servo positions and allows users to configure and move servos through a user-friendly interface. It also supports saving and applying servo configurations as presets.

### Main Components

#### Classes

1. **SerialBackend**
   - **Purpose**: Manages serial communication with the hardware.
   - **Responsibilities**:
     - Opens and closes the serial port.
     - Reads from and writes to the serial port using separate threads.
     - Handles message queuing for both incoming and outgoing data.

2. **PuppetGUI**
   - **Purpose**: Provides the main GUI for interacting with the servos.
   - **Responsibilities**:
     - Initializes the GUI layout and components.
     - Manages servo configurations and movements.
     - Handles user interactions such as button clicks and slider adjustments.
     - Updates the GUI based on real-time feedback from the servos.

#### Functions

1. **main()**
   - **Purpose**: Entry point of the application.
   - **Responsibilities**:
     - Parses command-line arguments.
     - Initializes the `SerialBackend` and `PuppetGUI`.
     - Starts the main event loop of the GUI.

2. **auto_port()**
   - **Purpose**: Automatically detects the serial port for communication.
   - **Responsibilities**:
     - Scans available serial ports and selects one based on specific criteria.

### Structure and Interaction

- **Serial Communication**: Managed by `SerialBackend`, which handles opening the port, reading incoming data, and sending commands. It uses threading to ensure non-blocking operations.
- **GUI Layout**: Managed by `PuppetGUI`, which uses the `tkinter` library to create a window with sliders, buttons, and text areas for controlling and monitoring servos.
- **Real-Time Feedback**: The GUI updates servo positions using a red dot on sliders to show actual angles received from the hardware.
- **Preset Management**: Users can save and apply servo configurations as presets, which are stored in a JSON file.

### External Dependencies

- **tkinter**: Used for creating the GUI.
- **serial**: Optional dependency for serial communication. The script checks for its availability and can run in a "dry-run" mode if not present.
- **json**: Used for loading and saving servo configurations.

### Notable Logic

- **Servo Configuration and Movement**: The script sends commands to move servos and configure their settings. It translates GUI angles to hardware angles considering servo limits.
- **Real-Time Updates**: Uses a method `_pump()` to continuously check for new data from the hardware and update the GUI accordingly.
- **JSON Handling**: Loads and saves servo presets in a JSON format, allowing for easy management of multiple configurations.

### Configuration Requirements

- **Serial Port**: The script requires a serial port to communicate with the hardware. It can automatically detect the port or use a specified one.
- **JSON File**: Presets are stored in `animations.json`, which the script reads and writes to manage servo configurations.

This script provides a comprehensive tool for managing servos in a robotics system, offering both manual control and automated configuration through presets.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\test.py
This Python script is designed to perform unit testing on the main components of an assistant application. It uses the `unittest` framework to ensure that various modules and functionalities are working as expected. Here's a detailed breakdown of the script:

### Overall Purpose

The script aims to validate the functionality of key components in an assistant application, including configuration loading, assistant initialization, conversation management, and interactions with language models and speech engines.

### Main Classes and Functions

1. **ColorfulTestCase**: A custom test case class that extends `unittest.TestCase`. It overrides assertion methods to potentially add custom behavior, such as colored output, although the current implementation simply calls the superclass methods.

2. **TestConfigLoad**: Tests the configuration loading functionality from the `main.py` module.
   - **test_load_config**: Ensures that the configuration is loaded correctly and contains all necessary keys.

3. **TestInitializationAssistant**: Tests the initialization of the assistant components.
   - **test_initialize_assistant**: Verifies that the assistant is initialized with the correct components and types.

4. **TestConversationLoop**: Tests the conversation loop functionality.
   - **test_conversation_loop_exit**: Simulates user input to test the conversation loop's ability to handle an "exit" command without errors.

5. **TestLLMFunctionality**: Tests the language model client.
   - **test_get_text**: Checks that the `get_text` method of the `GPTClient` returns a non-empty string.

6. **TestTTSFunctionality**: Tests the text-to-speech engine.
   - **test_generate_and_play**: Ensures that the TTS engine can generate and play audio, and that temporary files are cleaned up afterward.

7. **TestConversationManagerFunctionality**: Tests the conversation manager.
   - **test_add_and_get_conversation**: Validates that conversation messages are correctly added and retrieved.

### Structure and Interaction

- **Configuration and Initialization**: The script tests loading configurations and initializing the assistant with components like `ConversationManager`, `GPTClient`, `SpeechToTextEngine`, `TextToSpeechEngine`, and `ArduinoInterface`.

- **Conversation Loop**: Simulates user input to test the conversation loop's functionality, ensuring it handles commands like "exit" correctly.

- **Component Functionality**: Tests individual components such as the language model client, TTS engine, and conversation manager to ensure they perform their tasks correctly.

### External Dependencies and APIs

- **unittest**: The script uses Python's built-in `unittest` framework for testing.
- **yaml**: Used for configuration file handling.
- **io** and **sys**: Used for simulating user input and capturing output during tests.

### Notable Algorithms and Logic

- **Configuration Loading**: Ensures that the configuration file is correctly loaded and contains all necessary sections.
- **Assistant Initialization**: Verifies the correct setup of components, ensuring they are of the expected types.
- **Conversation Management**: Tests the ability to add and retrieve conversation entries, ensuring the conversation flow is maintained.
- **Temporary File Handling**: In the TTS test, it checks that temporary audio files are properly cleaned up after use.

### Configuration Requirements

The script assumes the presence of a `main.py` module with functions like `load_config`, `initialize_assistant`, and `conversation_loop`. It also relies on specific components like `ConversationManager`, `GPTClient`, `TextToSpeechEngine`, `SpeechToTextEngine`, and `ArduinoInterface` being correctly implemented and imported.

In summary, this script is a comprehensive set of unit tests designed to ensure the robustness and correctness of various components within an assistant application, focusing on configuration, initialization, and core functionalities.
