# AI Summary

### C:\GIT\Wheatley\Wheatley\Wheatley\python\src\main.py
Certainly! Here’s a detailed summary and analysis of the provided Python script, focusing on its **purpose, structure, main components, interactions, dependencies, configuration, and notable logic**.

---

## **Overall Purpose**

This script is the **main entry point for a voice-enabled AI assistant** called "Wheatley." It orchestrates the integration of several subsystems:
- **Speech-to-Text (STT)**: Converts user speech to text.
- **Large Language Model (LLM) Client**: Handles conversation and tool-calling via an LLM (e.g., OpenAI GPT).
- **Text-to-Speech (TTS)**: Converts the assistant’s responses to spoken output.
- **Arduino Hardware Interface**: Controls physical actuators (servos, LEDs) on a robot.
- **Event Loop**: Manages asynchronous user/system events and coordinates the above components.

The assistant can be run on systems with or without hardware (Arduino, Raspberry Pi GPIO), and supports both text and voice interaction.

---

## **Code Structure and Main Components**

### **1. Imports and Initialization**

- **Standard Libraries**: For logging, file I/O, async, timing, and typing.
- **Third-Party Libraries**: For YAML config, OpenAI API, colored terminal output, and hardware access.
- **Local Modules**: Import subsystems for hardware, assistant logic, LLM, TTS, and STT.

**Colorama** is initialized for colored terminal output. Logging is configured to write to a file (`assistant.log`) and suppress verbose logs from HTTP libraries.

---

### **2. Configuration and Welcome**

- **`load_config()`**: Loads YAML configuration (API keys, feature flags, model names, etc.).
- **`print_welcome()`**: Prints ASCII art and a welcome banner.

---

### **3. Assistant Initialization**

- **`initialize_assistant(config)`**:
  - Reads config to determine which features (STT, TTS) are enabled.
  - Initializes core components:
    - **ConversationManager**: Manages conversation history.
    - **GPTClient**: Handles LLM queries and tool calls.
    - **SpeechToTextEngine**: Manages speech recognition.
    - **TextToSpeechEngine**: Handles speech synthesis.
    - **ArduinoInterface**: Connects to Arduino hardware (with dry-run fallback if unavailable).
  - Handles platform-specific serial port detection for Arduino.
  - Returns all initialized components and feature flags.

---

### **4. Event Handling and Main Loop**

#### **Event Dataclass**
- **`Event`**: Simple container for events (source, payload, metadata, timestamp).

#### **Producers and Consumers**
- **`user_input_producer(q)`**: Async function that reads user text input and puts it into an event queue.
- **`get_event(queue)`**: Retrieves and normalizes events from the queue (handles both text and voice events).

#### **Event Processing**
- **`handle_non_user_event(event, manager)`**: Adds system messages to the conversation for timer/reminder events.
- **`process_event(event, manager, last_input)`**: Updates conversation history and checks for exit command.

#### **Tool Workflow**
- **`run_tool_workflow(manager, gpt_client, queue)`**:
  - Asks the LLM for a workflow (sequence of tool calls).
  - Executes tools via the `Functions` object.
  - Adds tool results to the conversation.

#### **Assistant Reply and Animation**
- **`generate_assistant_reply(manager, gpt_client)`**:
  - Gets assistant’s textual reply from the LLM.
  - Gets a matching animation (for the robot).
  - Updates conversation memory.

#### **TTS and Follow-Up**
- **`handle_tts_and_follow_up(...)`**:
  - Plays assistant’s reply via TTS.
  - If STT is enabled and the last input was voice, listens for a follow-up without requiring a hotword.
  - Manages hotword detection tasks.

#### **Async Conversation Loop**
- **`async_conversation_loop(...)`**:
  - Main event-driven loop.
  - Handles user/system events, processes them, runs tool workflows, generates replies, triggers animations, manages TTS/STT, and prints status.
  - Cleans up resources on exit.

#### **Async Task Debugging**
- **`print_async_tasks()`**: Prints a minimal list of running asyncio tasks for debugging.

---

### **5. Main Entry Point**

- **`main()`**:
  - Loads configuration and sets OpenAI API key.
  - Prints feature status (STT/TTS enabled or not).
  - Initializes all assistant components.
  - Prints welcome banner and initial servo status.
  - Starts the conversation with a greeting and gets the assistant’s introduction.
  - Plays the introduction via TTS or prints it.
  - Starts the main async conversation loop.
  - Handles shutdown and cleanup.

---

## **External Dependencies and APIs**

- **OpenAI API**: For LLM (GPT) responses and tool-calling.
- **RPi.GPIO**: For Raspberry Pi GPIO control (optional).
- **PySerial**: For Arduino serial communication.
- **colorama**: For colored terminal output.
- **yaml**: For configuration.
- **Local Modules**: Must be present in the project structure (`hardware.arduino_interface`, `assistant.assistant`, etc.).

---

## **Configuration Requirements**

- **YAML Config File**: Located at `config/config.yaml`, must include:
  - OpenAI API key.
  - Feature flags for STT and TTS.
  - LLM model name.
  - App-specific settings (e.g., conversation memory).
- **Hardware**: Arduino (via serial port) and optionally Raspberry Pi GPIO.

---

## **Notable Algorithms and Logic**

- **Asynchronous Event Loop**: Uses `asyncio` to handle user input, hotword detection, TTS playback, and hardware control concurrently.
- **Event Abstraction**: All user/system actions are wrapped as `Event` objects and processed uniformly.
- **Tool-Calling via LLM**: The assistant can ask the LLM for a workflow (sequence of tool calls), execute them, and integrate their results into the conversation.
- **Hotword and Follow-Up Handling**: After TTS playback, the assistant can listen for a follow-up voice command without requiring the hotword, improving conversational flow.
- **Dry-Run Mode**: If hardware is unavailable, the assistant can run in a simulated mode for development/testing.

---

## **Component Interactions**

- **User Input** (text or voice) → **Event Queue** → **ConversationManager** (updates history) → **GPTClient** (gets reply/workflow) → **Functions** (executes tools) → **ArduinoInterface** (controls hardware) → **TextToSpeechEngine** (speaks reply) → **SpeechToTextEngine** (listens for next input).
- **All subsystems are loosely coupled** via the event queue and conversation manager, allowing for modularity and extensibility.

---

## **Summary Table**

| Component                | Responsibility                                      |
|--------------------------|-----------------------------------------------------|
| `main()`                 | Entry point, initializes and launches assistant     |
| `initialize_assistant()` | Sets up all subsystems and hardware                 |
| `ConversationManager`    | Manages conversation history                        |
| `GPTClient`              | Handles LLM queries and tool-calling                |
| `Functions`              | Executes tool workflows suggested by LLM            |
| `TextToSpeechEngine`     | Converts text replies to speech                     |
| `SpeechToTextEngine`     | Converts user speech to text, manages hotword       |
| `ArduinoInterface`       | Controls robot hardware (servos, LEDs, etc.)        |
| `async_conversation_loop`| Orchestrates event-driven conversation flow         |
| `Event`                  | Encapsulates user/system actions for processing     |

---

## **Conclusion**

This script is a robust, modular, and extensible main controller for a conversational AI robot, integrating voice, LLM, and hardware control in a unified asynchronous framework. It is highly configurable, supports both text and voice interaction, and is designed for both development (dry-run) and deployment on hardware platforms.

### C:\GIT\Wheatley\Wheatley\Wheatley\python\src\puppet.py
Certainly! Here is a detailed summary and analysis of the provided Python script, **servo_puppet.py**.

---

## **Overall Purpose**

This script provides a **graphical user interface (GUI)** for controlling and configuring the servos and RGB LEDs of an OpenRB-150 / Core-2 robotic platform via a serial connection. The GUI allows users to:

- Adjust servo positions, velocities, idle bands, and intervals.
- Send commands to move servos or update their configuration.
- Save and apply servo/LED presets (called "animations").
- Monitor the actual servo positions as reported by the hardware.
- Control onboard LEDs, including a special "mic LED".
- View a log of all serial communications.

It is intended for users (likely developers or robotics enthusiasts) who need to interactively tune, test, and operate the robot's servos and LEDs.

---

## **Main Classes and Functions**

### **1. SerialBackend**

**Purpose:**  
Handles all serial communication with the hardware.

**Responsibilities:**
- Open and close the serial port.
- Start a background thread to read incoming serial data.
- Provide thread-safe queues for incoming (rx_q) and outgoing (tx_q) messages.
- Send text commands to the hardware.
- Support a "dry run" mode for testing without hardware.

**Key Methods:**
- `open()`: Opens the serial port and starts the reader thread.
- `_reader()`: Continuously reads lines from the serial port and puts them in the receive queue.
- `send(txt)`: Sends a command to the hardware (or just queues it in dry run).
- `close()`: Stops the reader thread and closes the port.

### **2. PuppetGUI (Tk subclass)**

**Purpose:**  
Implements the main GUI and all user interactions.

**Responsibilities:**
- Layout and manage all GUI widgets (servo sliders, buttons, log, etc.).
- Maintain servo configuration state (min/max, current/target angles, etc.).
- Handle user actions (moving sliders, pressing buttons, saving/applying presets).
- Parse and react to hardware responses.
- Visualize actual servo positions (red dots on sliders).
- Manage preset storage (load/save to JSON).
- Control LED color pickers and send LED commands.

**Key Methods:**
- `__init__()`: Initializes the GUI, loads presets, sets up the layout, and starts the periodic update loop.
- `_theme()`: Applies a custom theme to the GUI.
- `_layout()`: Arranges all widgets in the window.
- `_servo_row()`: Creates a row of widgets for each servo (slider, entries, buttons, etc.).
- `_draw_band()`: Draws the slider bar, idle band, tick marks, and the red dot showing actual servo position.
- `_led_row()`, `_preset_bar()`, `_log_area()`: Create corresponding control sections.
- `_save_preset()`, `_apply_preset()`: Save/apply servo and LED configurations as named presets.
- `_send_move()`, `_send_cfg_one()`, `_send_all()`: Send various servo commands to the hardware.
- `_send_led()`, `_send_mic_led()`: Send LED color commands.
- `_parse_servo_config_line()`, `_parse_move_line()`: Parse incoming serial lines to update GUI state.
- `_pump()`: Main periodic loop to process serial queues and update the GUI/log.

### **3. auto_port()**

**Purpose:**  
Tries to automatically detect the correct serial port for the hardware by scanning for USB/CP210 devices.

### **4. main()**

**Purpose:**  
Entry point for the script. Parses command-line arguments, sets up the serial backend, launches the GUI, and manages the application lifecycle.

---

## **Structure and Component Interaction**

- **Startup:**  
  - The script parses command-line arguments for serial port, baud rate, and dry-run mode.
  - It tries to auto-detect the serial port if not specified.
  - A `SerialBackend` is created and opened (unless in dry-run mode).
  - The `PuppetGUI` is instantiated, passing the backend for communication.
  - The GUI is started (`mainloop()`), and the backend is closed on exit.

- **GUI Operation:**  
  - The GUI displays a row for each servo, with sliders (for angle), entries (velocity, idle, interval), and buttons (move, configure).
  - The user can move sliders, adjust parameters, and send commands to the hardware.
  - The GUI periodically (every 50ms) checks for new serial messages and updates the log and servo state accordingly.
  - Actual servo positions (as reported by the hardware) are shown as red dots on each slider.
  - Presets (servo/LED settings) can be saved to or loaded from a JSON file.
  - LED controls allow direct color picking and sending to the hardware.

- **Serial Communication:**  
  - Outgoing commands are sent via the backend.
  - Incoming lines are parsed for servo configuration or move feedback, updating the GUI state.

---

## **External Dependencies and APIs**

- **Python Standard Library:**  
  - `argparse`, `json`, `os`, `queue`, `re`, `sys`, `threading`, `time`
  - `tkinter` and `tkinter.ttk` for GUI

- **Optional External Library:**  
  - `pyserial` (imported as `serial`): Required for actual serial communication. If not present, the script can run in dry-run mode.

- **Hardware/API Protocol:**  
  - The script expects the hardware to understand and respond to commands like:
    - `MOVE_SERVO;ID=...;TARGET=...;VELOCITY=...;`
    - `SET_SERVO_CONFIG:...`
    - `SET_LED;R=...;G=...;B=...;`
    - `SET_MIC_LED;IDX=...;R=...;G=...;B=...;`
    - `GET_SERVO_CONFIG`
  - It parses responses such as:
    - `SERVO_CONFIG:...`
    - `MOVE_SERVO;ID=...;TARGET=...;`
    - `Servo n: angle=...`

- **Configuration:**  
  - Presets are saved in a local JSON file (`animations.json`).
  - Serial port and baud rate can be set via command-line arguments.

---

## **Notable Algorithms and Logic**

- **Servo Value Mapping:**  
  - Each servo has configurable min/max limits.
  - GUI angles are mapped directly to hardware angles (1:1 mapping).
  - Presets store servo positions as normalized factors (0.0–1.0) between min and max, allowing them to adapt if limits change.

- **Idle Band Visualization:**  
  - Each servo slider shows an "idle band" (a colored region) indicating the allowed range around the target angle where the servo can idle.
  - The actual servo position is shown as a red dot, updated live from hardware feedback.

- **Preset Management:**  
  - Presets include servo velocities, target factors, idle ranges, intervals, and LED color.
  - They are saved in a compact, human-readable JSON format, with each animation on a new line.

- **Serial Threading:**  
  - Serial reading is done in a background thread to avoid blocking the GUI.
  - Communication between threads is handled via queues.

- **GUI State Locking:**  
  - The GUI disables all transmit (TX) controls until valid servo limits are received from the hardware, preventing invalid commands at startup.

- **Auto Port Detection:**  
  - Attempts to select the correct serial port by matching USB device descriptions.

---

## **Configuration Requirements**

- **Hardware:**  
  - OpenRB-150 / Core-2 platform with servos and addressable LEDs.
  - Serial connection to the host computer.

- **Software:**  
  - Python 3.x
  - `pyserial` (optional, but required for real hardware communication)
  - Tkinter (usually included with Python)

- **Files:**  
  - `animations.json` (created/updated by the script for presets)

- **Command-line Arguments:**  
  - `-p` or `--port`: Serial port (auto-detected if omitted)
  - `-b` or `--baud`: Baud rate (default 115200)
  - `--dry-run`: Run without hardware (for testing the GUI)

---

## **Summary Table of Key Features**

| Feature                | Description                                                                 |
|------------------------|-----------------------------------------------------------------------------|
| Servo Control          | Sliders and entries for position, velocity, idle band, interval per servo   |
| Actual Position Display| Red dot shows real servo angle from hardware feedback                       |
| Preset Management      | Save/apply named servo+LED configurations (animations)                      |
| LED Control            | Set RGB values for main and mic LEDs                                        |
| Serial Communication   | Threaded, with log and auto port detection                                  |
| GUI Locking            | Controls disabled until servo limits received                               |
| Dry Run Mode           | Allows GUI use without hardware                                             |
| Log Area               | Shows all sent/received serial messages                                     |

---

## **Conclusion**

This script is a robust, user-friendly GUI tool for tuning, testing, and operating the servos and LEDs of an OpenRB-150/Core-2 robot via serial commands. It combines real-time feedback, configuration management, and preset storage in a single interface, with careful attention to usability and safety (e.g., GUI locking, live feedback). It is modular, with clear separation between the GUI and serial backend, and is extensible for further robotics applications.

### C:\GIT\Wheatley\Wheatley\Wheatley\python\src\test.py
Certainly! Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script is a **unit test suite** for a modular voice assistant application. Its primary goal is to verify the correct operation of the assistant’s main modules, including configuration loading, initialization, conversation management, LLM (Large Language Model) interaction, text-to-speech (TTS), speech-to-text (STT), and hardware interfacing. The tests are meant to be run automatically (e.g., via CI/CD or during development) to ensure that changes to the codebase do not break core functionality.

---

## **Structure and Main Components**

### **1. Imports and Dependencies**

- **Standard Library:**  
  - `unittest`: For structuring and running the tests.
  - `os`, `io`, `sys`: For file and I/O operations, and simulating user input/output.
  - `yaml`: Presumably for configuration file parsing (though not directly used in this script).

- **Project Modules:**  
  - `main`: Contains the main entry points and initialization logic for the assistant.
  - `assistant.assistant`: Contains `ConversationManager` for managing the conversation state.
  - `llm.llm_client`: Contains `GPTClient` for LLM interactions and `Functions` (not used in this script).
  - `tts.tts_engine`: Contains `TextToSpeechEngine` for TTS.
  - `stt.stt_engine`: Contains `SpeechToTextEngine` for STT.
  - `hardware.arduino_interface`: Contains `ArduinoInterface` for hardware control.

**External Dependencies:**  
- The script assumes the presence of the above modules and their dependencies (e.g., LLM APIs, TTS/STT engines, hardware drivers).
- Likely requires configuration files (YAML) and possibly hardware or API credentials.

---

### **2. Custom Test Base Class**

- **`ColorfulTestCase`**:  
  - Inherits from `unittest.TestCase`.
  - Overrides some assertion methods (though currently just calls the parent methods; possibly a placeholder for future colored output).

---

### **3. Test Classes and Their Responsibilities**

#### **a. TestConfigLoad**

- **Purpose:**  
  - Verifies that the assistant’s configuration loader (`main.load_config`) works and returns a dictionary with all required top-level keys.

#### **b. TestInitializationAssistant**

- **Purpose:**  
  - Tests the assistant initialization process (`main.initialize_assistant`).
  - Ensures that all core components (conversation manager, LLM client, STT/TTS engines, Arduino interface, and feature flags) are instantiated and of the correct types.

#### **c. TestConversationLoop**

- **Purpose:**  
  - Tests the main conversation loop (`main.conversation_loop`).
  - Simulates user input ("exit") by redirecting `sys.stdin` and captures output by redirecting `sys.stdout`.
  - Ensures the loop can start and exit gracefully and that user prompts are displayed.

#### **d. TestLLMFunctionality**

- **Purpose:**  
  - Tests the LLM client’s ability to generate text responses (`GPTClient.get_text`).
  - Ensures the output is a non-empty string and that no exceptions are raised.

#### **e. TestTTSFunctionality**

- **Purpose:**  
  - Tests the TTS engine’s ability to generate, play, and clean up temporary audio files (`TextToSpeechEngine.generate_and_play_advanced`).
  - Ensures no temporary files remain after playback.

#### **f. TestConversationManagerFunctionality**

- **Purpose:**  
  - Tests the conversation manager’s ability to add and retrieve conversation turns.
  - Ensures that user and assistant messages are correctly stored and retrievable.

---

## **How Components Interact**

- **Configuration Loading:**  
  - `main.load_config()` reads and parses the configuration, which is then used for initializing all assistant components.

- **Initialization:**  
  - `main.initialize_assistant(config)` creates instances of all core modules, passing configuration as needed.

- **Conversation Loop:**  
  - `main.conversation_loop(...)` orchestrates the interaction between the user, LLM, TTS/STT, and hardware. The test simulates a user typing "exit" to ensure the loop can terminate gracefully.

- **LLM, TTS, STT, Hardware:**  
  - Each has its own class, instantiated and tested independently to ensure modularity and testability.

---

## **Notable Algorithms and Logic**

- **Input/Output Simulation:**  
  - The test for the conversation loop uses `io.StringIO` to simulate user input and capture output, allowing automated testing of interactive code.

- **Temporary File Cleanup:**  
  - The TTS test checks that temporary audio files are deleted after playback, ensuring good resource management.

- **Conversation Management:**  
  - The conversation manager is tested for correct history tracking and message storage.

---

## **External Dependencies, APIs, and Configuration**

- **APIs:**  
  - The LLM client likely interacts with an external API (e.g., OpenAI GPT).
  - TTS and STT engines may use cloud or local APIs.
  - The Arduino interface communicates with hardware.

- **Configuration:**  
  - The script expects a configuration file with sections for app, logging, stt, tts, llm, hardware, assistant, and secrets.
  - Paths and credentials for APIs/hardware are likely required.

---

## **Summary Table**

| Component/Class              | Responsibility                                         |
|------------------------------|-------------------------------------------------------|
| `ColorfulTestCase`           | Base test case (potential for colored output)         |
| `TestConfigLoad`             | Tests configuration loading                           |
| `TestInitializationAssistant`| Tests assistant initialization                        |
| `TestConversationLoop`       | Tests main conversation loop (user interaction)       |
| `TestLLMFunctionality`       | Tests LLM text generation                             |
| `TestTTSFunctionality`       | Tests TTS audio generation and cleanup                |
| `TestConversationManagerFunctionality` | Tests conversation history management   |

---

## **Conclusion**

This script is a comprehensive unit test suite for a modular voice assistant system. It ensures that configuration, initialization, conversation management, LLM, TTS, and hardware modules work as expected and interact correctly. The tests are designed to catch regressions and integration issues early, and they rely on both simulated and real interactions with the assistant’s components. The script assumes the presence of several external dependencies, including configuration files, APIs, and possibly hardware.
