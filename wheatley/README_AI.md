# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\main.py
Certainly! Here is a **detailed summary and analysis** of the provided Python script, including its overall purpose, architecture, main classes and functions, configuration, dependencies, and notable logic.

---

## **Overall Purpose**

This script is the **main entry point** for the "Wheatley assistant," a multimodal AI assistant that integrates:

- **Speech-to-text (STT)** for voice input,
- **Large Language Model (LLM)** (e.g., OpenAI GPT) for conversation and tool use,
- **Text-to-speech (TTS)** for voice output,
- **Arduino hardware interface** for controlling servos and LED animations on a physical robot.

It orchestrates these components using an **asynchronous event loop** that reacts to user input (text or speech), processes it through the LLM, possibly invokes tools, generates a response, and controls the robot's hardware for expressive feedback.

---

## **Code Structure and Flow**

### **1. Imports and Initialization**

- **Standard libraries**: For async operations, logging, config parsing, CLI, etc.
- **Third-party libraries**: `yaml` for config, `openai` for LLM, `colorama` for colored output, etc.
- **Local modules**: Hardware interface, conversation manager, LLM client, TTS/STT engines, timing utilities.

**Logging** is set up to only log to a file, with verbose logs from HTTP libraries suppressed.

---

### **2. Configuration and Welcome**

- **`load_config()`**: Loads YAML configuration (API keys, feature flags, model names, etc.).
- **`print_welcome()`**: Prints ASCII art and a welcome banner.

---

### **3. Assistant Initialization**

- **`initialize_assistant()`**: Central function to instantiate all major subsystems:
  - **ConversationManager**: Tracks conversation history and memory.
  - **GPTClient**: Handles LLM API calls and tool invocation.
  - **SpeechToTextEngine** and **TextToSpeechEngine**: For voice input/output, if enabled.
  - **ArduinoInterface**: Connects to the robot hardware (auto-detects serial port, supports dry-run if unavailable).
  - Loads long-term memory into the conversation context.
  - Returns all initialized components and feature flags.

---

### **4. Event Handling**

- **`Event` dataclass**: Represents an event in the system (source, payload, metadata).
- **`user_input_producer()`**: Async producer that reads user text input and puts it into an event queue.
- **`get_event()`**: Normalizes events from the queue, especially voice events.
- **`handle_non_user_event()`**: Handles system events (timers, reminders) by injecting system messages into conversation history.
- **`process_event()`**: Updates conversation history and checks for exit commands.

---

### **5. Tool and LLM Interaction**

- **`run_tool_workflow()`**: 
  - Asks the LLM for a proposed workflow (sequence of tool calls).
  - Executes tool calls via the `Functions` interface.
  - Updates conversation with tool results.
  - Handles web search results specially.
  - Refreshes long-term memory before tool execution.

- **`generate_assistant_reply()`**:
  - Gets the LLM's textual reply and a suggested animation for the robot.
  - Updates conversation history and prints memory.

---

### **6. Output and Follow-up**

- **`handle_tts_and_follow_up()`**:
  - Plays the assistant's reply via TTS (if enabled).
  - Manages hotword detection and follow-up voice input.
  - Pauses/resumes STT as needed to avoid conflicts with TTS playback.
  - Supports a 5-second follow-up window for voice input after TTS.

---

### **7. Main Async Loop**

- **`async_conversation_loop()`**:
  - Main event loop: waits for events (user input, voice, etc.), processes them, runs tools, gets LLM reply, controls hardware, and manages TTS/STT.
  - Handles graceful shutdown and cleanup.

- **`print_async_tasks()`**: Debug utility to print active async tasks.

---

### **8. Main CLI Entry Point**

- **`main()`**:
  - Parses CLI args (e.g., export timings).
  - Loads config and API keys.
  - Authenticates external services (OpenAI, ElevenLabs, etc.).
  - Initializes all components.
  - Prints feature status.
  - Sets initial animation and gets an introductory LLM reply.
  - Starts the async conversation loop.
  - Handles shutdown and cleanup.

---

## **External Dependencies and APIs**

- **OpenAI API**: For LLM (GPT) interaction. Requires API key in config.
- **ElevenLabs API** (implied): For advanced TTS, checked in service authentication.
- **YAML config file**: For all settings, API keys, feature flags.
- **Arduino hardware**: For robot control (servos, LEDs), via serial port.
- **Colorama**: For colored terminal output.
- **Other local modules**: For hardware, LLM, TTS, STT, and utility logic.

---

## **Configuration Requirements**

- **config/config.yaml**: Must exist and provide all necessary settings (API keys, model names, feature flags).
- **API keys**: For OpenAI and TTS (e.g., ElevenLabs).
- **Arduino**: Connected via serial port, or script runs in dry-run mode if not detected.

---

## **Notable Algorithms and Logic**

- **Asynchronous Event Loop**: Uses asyncio to handle user input (text and voice), tool execution, LLM calls, and hardware control concurrently.
- **Tool Use via LLM**: The LLM can propose a sequence of tool calls (workflow), which are executed and their results fed back into the conversation.
- **Voice Interaction**: Hotword detection and follow-up voice input are managed to allow natural, hands-free conversation.
- **Hardware Feedback**: The LLM suggests animations, which are mapped to servo/LED actions on the robot.
- **Robustness**: Handles missing hardware, API failures, and supports dry-run mode for development.

---

## **Component Interactions**

1. **User Input** (text or voice) → **Event Queue**
2. **Event Loop** pulls events, updates **ConversationManager**
3. **GPTClient** is queried for reply and tool workflow
4. **Functions** executes any tool calls, updates conversation
5. **GPTClient** provides reply text and animation
6. **ArduinoInterface** sets animation on robot hardware
7. **TextToSpeechEngine** plays reply (if enabled)
8. **SpeechToTextEngine** listens for follow-up (if enabled)
9. Loop continues until user exits

---

## **Summary Table**

| Component                | Responsibility                                  |
|--------------------------|-------------------------------------------------|
| `ConversationManager`    | Tracks and updates conversation history/memory  |
| `GPTClient`              | LLM API calls, gets reply, proposes tools       |
| `Functions`              | Executes tool calls suggested by LLM            |
| `SpeechToTextEngine`     | Captures and transcribes voice input            |
| `TextToSpeechEngine`     | Generates and plays speech output               |
| `ArduinoInterface`       | Controls robot hardware (servos, LEDs)          |
| `Event`                  | Represents events in async loop                 |

---

## **Conclusion**

This script is a robust, extensible, and hardware-integrated AI assistant framework. It combines real-time multimodal interaction (text, voice, hardware), LLM-driven conversation and tool use, and asynchronous event-driven architecture. It is highly configurable and designed for both development (dry-run) and deployment with real hardware.

### C:\GIT\Wheatly\Wheatley\Wheatley\present_timeline.py
Certainly! Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script implements a **Tkinter-based GUI application** that visualizes timing and log data from external files. Its main functions are:

- **Display a timeline (Gantt chart) of events/functions** from timing data, with durations and color-coding by functionality.
- **Show summary statistics** (average duration per functionality) as a bar chart.
- **Display log file entries** in a text widget.
- **Enable interactive exploration**: zooming (both axes), panning, and file selection for both timing and log data.

---

## **Main Classes and Functions**

### **1. Helper Functions**

- **`load_timings(path)`**
  - Loads a JSON file (default: `timings.json`) containing timing data.
  - Returns a list of timing entries or an empty list if the file doesn't exist.

- **`load_logs(path)`**
  - Loads and parses a log file (default: `assistant.log`).
  - Uses a regular expression to extract timestamp, log level, and message from each line.
  - Returns a list of log event dictionaries.

---

### **2. Main GUI Class: `TimelineGUI`**

This class inherits from `tk.Tk` and encapsulates the entire GUI logic.

#### **Initialization and Layout**

- **`__init__`**
  - Initializes the main window, sets title and size.
  - Sets default file paths for timing and log files.
  - Calls methods to create widgets and load data.

- **`_make_widgets`**
  - Constructs the GUI layout:
    - Top bar with buttons to reload data or select files.
    - Tabbed notebook with three tabs:
      - **Timeline** (Gantt chart)
      - **Time Summary** (bar chart)
      - **Logs** (text display)

#### **File Selection**

- **`_pick_timing`** and **`_pick_log`**
  - Open file dialogs for the user to select timing or log files.
  - Update the relevant file path and reload all data.

#### **Data Loading and Refresh**

- **`_reload_everything`**
  - Loads timing and log data using the helper functions.
  - Refreshes all three tabs by calling their respective drawing/display methods.

#### **Visualization and Display**

- **`_draw_timeline`**
  - Clears the timeline tab.
  - Processes timing data:
    - Converts start times to `datetime` and durations to seconds.
    - Sorts entries chronologically.
    - Assigns unique colors to each functionality.
    - Plots a horizontal bar chart (Gantt chart) using Matplotlib, with:
      - Time on the x-axis (formatted as dates).
      - Functionality labels on the y-axis.
      - Bar widths proportional to duration (converted from seconds to fractions of a day).
      - Color legend for functionalities.
      - Duration annotations on each bar.
    - Embeds the plot in the Tkinter tab using `FigureCanvasTkAgg`.
    - Adds a Matplotlib navigation toolbar for pan/zoom/save.
    - Implements custom mouse wheel zoom:
      - **Wheel**: horizontal (time) zoom.
      - **Shift+Wheel**: vertical (label) zoom.

- **`_draw_summary`**
  - Clears the summary tab.
  - Computes average duration per functionality.
  - Plots a horizontal bar chart of these averages.
  - Annotates each bar with its value.
  - Embeds the plot in the Tkinter tab.

- **`_show_logs`**
  - Clears and repopulates the log tab's text widget.
  - Displays each log entry in a formatted manner.

---

## **Structure and Component Interaction**

- The **main window** is a `TimelineGUI` instance.
- **Helper functions** load and parse data from files.
- **Tabs** separate the three main views (timeline, summary, logs).
- **Matplotlib** is used for all plotting, embedded in Tkinter via the `FigureCanvasTkAgg` backend.
- **User actions** (button clicks, file selections, mouse wheel) trigger data reloads or interactive plot navigation.
- **Data flow**: File → Helper function → GUI class → Matplotlib plot or text widget.

---

## **External Dependencies**

- **Standard Library**: `os`, `json`, `datetime`, `tkinter`, `collections`, `re`
- **Matplotlib**: For plotting and embedding charts in the GUI.
- **Tkinter**: For the GUI framework and widgets.
- **No third-party dependencies** beyond Matplotlib.

---

## **APIs and Configuration**

- **File Inputs**:
  - **Timing file**: JSON format, default name `timings.json`. Each entry should have at least `startTime`, `durationMs`, and `functionality`.
  - **Log file**: Plain text, default name `assistant.log`. Each line should match the regex:  
    `YYYY-MM-DD HH:MM:SS LEVEL: message`
- **No external APIs** or network requirements.
- **Configuration**: File paths can be changed via the GUI.

---

## **Notable Algorithms and Logic**

- **Gantt Chart Width Calculation**:
  - Durations are stored in milliseconds, converted to seconds, then to fractions of a day (for Matplotlib's date axis).
- **Color Assignment**:
  - Each unique functionality is mapped to a unique color using Matplotlib's `tab20` colormap.
- **Mouse Wheel Zoom**:
  - Custom event handler for Matplotlib's `scroll_event`:
    - Normal wheel zooms x-axis (time).
    - Shift+wheel zooms y-axis (labels).
    - Zoom is centered on the mouse pointer.
    - Zoom step is configurable (`ZOOM_STEP`).
- **Legend and Annotation**:
  - Automatic legend for functionality colors.
  - Each bar is annotated with its duration or average time.
- **File Dialogs**:
  - Standard Tkinter dialogs for file selection, with filters for JSON/log files.

---

## **Summary**

This script provides an interactive, user-friendly GUI for visualizing timing and log data. It is well-structured, modular, and leverages Matplotlib for powerful plotting within a Tkinter interface. The application is suitable for analyzing the chronological sequence and duration of various functionalities (e.g., in a software assistant or automated process), and for reviewing associated log events. Its interactive features (zoom, pan, file selection) make it flexible for exploratory data analysis.

**No advanced algorithms** are present; the logic is straightforward, focusing on robust data handling, user interaction, and clear visualization. The most notable implementation detail is the custom zoom handler for Matplotlib plots embedded in Tkinter.

### C:\GIT\Wheatly\Wheatley\Wheatley\puppet.py
Certainly! Here’s a detailed summary of the provided `servo_puppet.py` script, covering its purpose, structure, main classes and functions, dependencies, configuration, and notable logic.

---

## **Overall Purpose**

The script provides a **graphical user interface (GUI)** to control and configure servos connected to an OpenRB-150 or Core-2 microcontroller board. It allows users to:

- Move individual servos to specific angles.
- Adjust servo parameters (velocity, idle band, interval).
- Send configuration commands to the hardware.
- Save and apply animation presets.
- Control onboard LEDs.
- View live feedback from the hardware, including actual servo positions.

The GUI is built with **Tkinter** and communicates with the hardware via a serial connection.

---

## **Main Components**

### 1. **Constants and Configuration**

- **SERVO_NAMES**: List of servo names (e.g., lens, eyelid1, eyeX, etc.).
- **DEFAULT_MIN/MAX**: Default min/max angles for each servo.
- **UI Colors and Layout Constants**: Colors for UI elements, bar heights, etc.
- **Column Indexes**: For organizing the grid layout.

---

### 2. **Serial Communication Layer**

#### **SerialBackend Class**

- **Purpose**: Abstracts serial communication with the hardware.
- **Responsibilities**:
  - Manages opening/closing the serial port.
  - Handles sending and receiving messages (with optional dry-run mode).
  - Runs a background thread to read incoming serial data and queues it for the GUI.
  - Provides queues for RX (received) and TX (sent) messages for thread-safe communication.
- **Notable Logic**:
  - Handles absence of the `serial` module gracefully (for dry-run/testing).
  - Uses a thread to avoid blocking the GUI.

---

### 3. **Graphical User Interface**

#### **PuppetGUI Class (inherits from Tk)**

- **Purpose**: Implements the main window and all UI logic.
- **Responsibilities**:
  - **Theme/Styling**: Sets up the look and feel using Tkinter’s `ttk.Style`.
  - **Layout**: Organizes the window into two panes:
    - **Left Pane**: Servo controls (sliders, parameter entries, move/config buttons, LED controls, preset management).
    - **Right Pane**: Log area for serial communication and status messages.
  - **Servo Control Rows**: For each servo, provides:
    - A slider for target angle.
    - Entry fields for velocity, idle band, interval.
    - Buttons for moving/configuring the servo.
    - A canvas showing the slider, idle band, and a red dot for the actual angle reported by the hardware.
  - **LED Controls**: RGB entries, color picker, and buttons to send LED commands.
  - **Preset Management**:
    - Save current settings as a preset (animation).
    - Apply a preset to all servos and LEDs.
    - Presets are stored in a JSON file (`animations.json`).
  - **Command Sending**:
    - Sends commands to move/configure servos and set LEDs.
    - Can send all servo configs at once.
  - **Feedback and Parsing**:
    - Parses incoming serial lines to update servo limits and actual angles.
    - Updates the UI to reflect live hardware state (e.g., red dot on sliders).
  - **Utilities**: Color picker, message logging, enabling/disabling controls.
  - **Event Loop**: Uses a periodic `after` callback (`_pump`) to process serial queues and update the UI.

---

### 4. **Preset and Animation Management**

- **Presets**: Saved as JSON objects with servo velocities, target factors (normalized positions), idle ranges, intervals, and LED color.
- **Loading/Saving**: Presets are loaded at startup and saved when the user creates a new one.
- **Applying**: When a preset is applied, all servo controls and LED fields are updated, and the configuration is sent to the hardware.

---

### 5. **Command and Feedback Protocol**

- **Outgoing Commands**:
  - `MOVE_SERVO;ID=...;TARGET=...;VELOCITY=...;`
  - `SET_SERVO_CONFIG:...` (for all servos or one at a time)
  - `SET_LED;R=...;G=...;B=...;`
  - `SET_MIC_LED;R=...;G=...;B=...;`
- **Incoming Feedback**:
  - `SERVO_CONFIG:...` lines update the min/max for each servo.
  - `MOVE_SERVO;ID=...;TARGET=...;` or `Servo n: angle=...` lines update the actual angle shown on the GUI.

---

### 6. **Startup and Main Loop**

- **Argument Parsing**: Supports command-line options for serial port, baud rate, and dry-run mode.
- **Auto Port Detection**: Tries to auto-detect the serial port if not specified.
- **Initialization**:
  - Starts the serial backend.
  - Instantiates the GUI.
  - Requests servo configuration from the hardware.
  - Enters the Tkinter main loop.
- **Graceful Shutdown**: Closes the serial port on exit.

---

## **External Dependencies**

- **Tkinter**: For the GUI (standard in Python, but may require installation on some systems).
- **pyserial**: For serial communication (`import serial`). If not installed, the script can run in dry-run mode for UI testing.
- **animations.json**: A local file for saving/loading presets (created if not present).

---

## **Configuration Requirements**

- **Serial Port**: Must be specified or auto-detected unless running in dry-run mode.
- **Baud Rate**: Default is 115200, can be changed via command-line.
- **Hardware**: Expects an OpenRB-150 or Core-2 board running compatible firmware.

---

## **Notable Algorithms and Logic**

- **Live Feedback Visualization**: The GUI displays both the target angle (slider position) and the actual angle (red dot) as reported by the hardware, providing real-time feedback.
- **Idle Band Visualization**: Each servo row’s canvas shows the allowed idle band as a colored bar.
- **Preset Normalization**: Presets store servo positions as normalized factors (0.0–1.0 between min and max), allowing them to adapt to different hardware limits.
- **Threaded Serial Reading**: Serial reads are performed in a background thread, with queues used for safe communication with the main GUI thread.
- **UI Locking**: Controls are disabled until servo limits are received from the hardware, preventing invalid commands.

---

## **Component Interactions**

- **SerialBackend** handles all serial I/O, providing queues for the GUI to read/write messages.
- **PuppetGUI** manages the user interface, periodically polling the serial queues to update the UI and send commands.
- **Preset Management** interacts with both the GUI and the file system (for JSON storage).
- **Command/Feedback Parsing** ensures the GUI state matches the hardware state, updating controls and visualizations as needed.

---

## **Summary Table**

| Component         | Responsibility                                                |
|-------------------|--------------------------------------------------------------|
| SerialBackend     | Serial I/O, background reading, message queuing              |
| PuppetGUI         | Main window, servo controls, LED controls, logging, parsing  |
| Preset Management | Save/load/apply servo/LED settings as named animations       |
| Command Protocol  | Text-based commands for servo/LED control and feedback       |
| Main Loop         | Argument parsing, startup, shutdown                          |

---

## **Conclusion**

This script is a comprehensive, user-friendly tool for configuring and controlling a multi-servo robotic device via serial communication. It provides live feedback, preset management, and robust error handling, making it suitable for both development and operation of animatronic or robotic systems using OpenRB-150/Core-2 hardware. The code is modular, with clear separation between GUI, serial communication, and configuration management.

### C:\GIT\Wheatly\Wheatley\Wheatley\service_auth.py
Certainly! Here’s a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script provides authentication helpers for a project called "Wheatley." Its main goal is to check and report whether the application can successfully authenticate with several external services (Google, Spotify, OpenAI, and ElevenLabs) using credentials stored in a YAML configuration file. It also initializes agent objects for Google and Spotify if authentication is successful.

---

## **Main Components**

### **1. Configuration Loader**

- **Function:** `_load_config`
- **Responsibility:** Loads and parses a YAML configuration file (`config.yaml`) located in a `config` directory relative to the script. This file is expected to contain API keys and other secrets required for authenticating with external services.

### **2. Service Authentication Checkers**

- **Function:** `_check_openai`
  - **Responsibility:** Attempts to authenticate with the OpenAI API using the provided API key. It supports both the new and old versions of the OpenAI Python library by checking for the presence of the `OpenAI` class.
  - **Logic:** If authentication is successful (i.e., a list of models can be retrieved), returns `True`; otherwise, returns `False`.

- **Function:** `_check_elevenlabs`
  - **Responsibility:** Attempts to authenticate with the ElevenLabs API using the provided API key. It tries to retrieve all available voices as a test of credentials.
  - **Logic:** Returns `True` if successful, `False` otherwise.

### **3. Service Agent Initialization**

- **GoogleAgent** and **SpotifyAgent**:
  - **Purpose:** These are classes (imported from local modules) that encapsulate logic for interacting with Google and Spotify APIs, respectively.
  - **Initialization:** The script tries to instantiate these agents and perform a simple operation (listing calendars for Google, getting current playback for Spotify) to verify authentication.

### **4. Authentication Orchestrator**

- **Function:** `authenticate_services`
  - **Responsibility:** Coordinates the authentication process for all supported services:
    - Loads configuration.
    - Attempts to authenticate with Google and Spotify by initializing their respective agents and performing a test operation.
    - Checks OpenAI and ElevenLabs authentication using their respective helper functions.
    - Prints the authentication status for each service using colored output (green for success, red for failure).
    - Updates a global `SERVICE_STATUS` dictionary with the results.
    - Returns a dictionary mapping service names to their authentication status.

---

## **Code Structure and Interactions**

- **Global Variables:**  
  - `SERVICE_STATUS`: Tracks authentication status for each service.
  - `GOOGLE_AGENT`, `SPOTIFY_AGENT`: Hold initialized agent objects if authentication is successful.

- **Imports and Dependencies:**
  - **External Libraries:**  
    - `openai` (optional, for OpenAI API)
    - `elevenlabs` (optional, for ElevenLabs API)
    - `colorama` (for colored terminal output)
    - `yaml` (for reading configuration)
  - **Local Modules:**  
    - `llm.google_agent` and `llm.spotify_agent` (for agent classes)
  - **Fallback Imports:**  
    - Tries both relative and absolute imports for agent classes to support different execution contexts.

- **Error Handling:**  
  - Uses broad exception handling to ensure that missing libraries or failed authentications do not crash the script, but are reported as failures.

- **Configuration Requirements:**  
  - Expects a YAML file at `config/config.yaml` relative to the script, containing a `secrets` section with API keys for OpenAI and ElevenLabs.

---

## **Notable Algorithms and Logic**

- **Dynamic Library Support:**  
  - The script detects at runtime whether the `openai` and `elevenlabs` libraries are installed, allowing it to run even if some dependencies are missing (e.g., during documentation builds).

- **Version Compatibility:**  
  - The OpenAI checker supports both the new and old versions of the OpenAI Python library by checking for the existence of the `OpenAI` class.

- **Service Verification:**  
  - Authentication is verified not just by instantiating clients, but by making a simple API call (e.g., listing models, listing voices, listing calendars, getting playback) to ensure credentials are valid and the service is reachable.

- **User Feedback:**  
  - Uses `colorama` to print colored checkmarks or crosses for each service, providing clear visual feedback on authentication status.

---

## **External Dependencies and Configuration**

- **Required Python Packages:**
  - `PyYAML` (for YAML parsing)
  - `colorama` (for colored output)
  - Optionally: `openai`, `elevenlabs`, and any dependencies of `GoogleAgent` and `SpotifyAgent`

- **Configuration File:**
  - `config/config.yaml` must exist and contain at least:
    ```yaml
    secrets:
      openai_api_key: "..."
      elevenlabs_api_key: "..."
    ```

- **Agent Classes:**
  - `GoogleAgent` and `SpotifyAgent` must be implemented and importable from the specified modules.

---

## **Summary Table**

| Component        | Purpose                                              | Key Logic/Behavior                                  |
|------------------|-----------------------------------------------------|-----------------------------------------------------|
| `_load_config`   | Load YAML config with API keys                      | Reads and parses config file                        |
| `_check_openai`  | Validate OpenAI API key                             | Supports multiple library versions, lists models    |
| `_check_elevenlabs` | Validate ElevenLabs API key                      | Lists voices to verify credentials                  |
| `authenticate_services` | Authenticate all services, print status      | Orchestrates checks, prints colored output, updates global status |
| `GoogleAgent`/`SpotifyAgent` | Service-specific API wrappers           | Instantiated and tested for authentication          |

---

## **Conclusion**

This script is a robust, user-friendly authentication helper for a multi-service Python application. It abstracts away the details of authenticating with several APIs, provides clear feedback to the user, and gracefully handles missing dependencies or failed authentications. It is designed to be extensible and maintainable, with clear separation of concerns for configuration loading, authentication checking, and user feedback.

### C:\GIT\Wheatly\Wheatley\Wheatley\test.py
Certainly! Here’s a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script is a **unit test suite** for a modular Python-based assistant application named "Wheatley." It exercises and validates the core modules and functionalities of the assistant, including configuration loading, component initialization, conversation handling, language model (LLM) interaction, text-to-speech (TTS), speech-to-text (STT), hardware interfacing, and long-term memory management.

---

## **Main Classes and Functions**

### **1. ColorfulTestCase**
- **Purpose:** Custom subclass of `unittest.TestCase` (though not adding color output, just overriding some assertion methods).
- **Responsibilities:** Provides a base for all test cases, potentially for future extension (e.g., colored output).

---

### **2. TestConfigLoad**
- **Purpose:** Tests configuration loading as used in `main.py`.
- **Responsibilities:** Ensures that the configuration file is loaded and contains all required keys (e.g., app, logging, stt, tts, llm, hardware, assistant, secrets).

---

### **3. TestInitializationAssistant**
- **Purpose:** Tests assistant initialization logic.
- **Responsibilities:** Verifies that the `initialize_assistant` function returns all expected components (ConversationManager, GPTClient, STT/TTS engines, ArduinoInterface, and boolean flags for STT/TTS enablement).

---

### **4. TestConversationLoop**
- **Purpose:** Tests the main conversation loop logic.
- **Responsibilities:** Simulates user input (specifically "exit") to ensure the loop can start and exit cleanly. Redirects `sys.stdin` and `sys.stdout` to simulate and capture input/output.

---

### **5. TestLLMFunctionality**
- **Purpose:** Tests the GPT-based language model client.
- **Responsibilities:** Ensures that the LLM client (`GPTClient`) can process a conversation and return a non-empty string response.

---

### **6. TestTTSFunctionality**
- **Purpose:** Tests the text-to-speech engine.
- **Responsibilities:** Ensures that the TTS engine can generate, play, and clean up temporary audio files after speaking.

---

### **7. TestConversationManagerFunctionality**
- **Purpose:** Tests the assistant's conversation management.
- **Responsibilities:** Ensures that the conversation manager can add user/assistant messages and retrieve the conversation history correctly.

---

### **8. TestLongTermMemory**
- **Purpose:** Tests the long-term memory utilities.
- **Responsibilities:** Verifies that memory can be overwritten, edited, and read, and that long text fields are truncated as expected.

---

## **Structure and Component Interaction**

- **Test Classes:** Each test class targets a specific module or functionality.
- **Test Methods:** Each method within a class tests a specific aspect (e.g., loading config, adding conversation, generating TTS).
- **Setup:** Tests typically initialize components using the same logic as the main application (via `main.load_config()` and `main.initialize_assistant()`).
- **Simulation:** For interactive components (like the conversation loop), the script simulates user input/output using `io.StringIO` and redirects `sys.stdin`/`sys.stdout`.
- **Assertions:** The script uses assertions to check types, return values, and side effects (like file cleanup).

---

## **External Dependencies and APIs**

- **Wheatley Modules:** The script imports from various `wheatley` submodules:
  - `wheatley.main`: Main entry point, configuration, and initialization logic.
  - `wheatley.assistant.assistant`: Conversation management.
  - `wheatley.llm.llm_client`: GPT-based LLM client.
  - `wheatley.tts.tts_engine`: Text-to-speech engine.
  - `wheatley.stt.stt_engine`: Speech-to-text engine.
  - `wheatley.hardware.arduino_interface`: Hardware interface (Arduino).
  - `wheatley.utils.long_term_memory`: Memory utilities.

- **Standard Library:** Uses `unittest`, `os`, `io`, and `sys`.

- **Configuration Requirements:** The tests assume the presence of a configuration file or system that `main.load_config()` can access, with specific keys.

- **Temporary Files:** TTS tests expect a `temp` directory for audio files, and long-term memory tests create/delete a temporary JSON file.

---

## **Notable Algorithms and Logic**

- **Conversation Loop Simulation:** The test for the conversation loop simulates user input by redirecting `sys.stdin` to a `StringIO` object containing "exit\n". This allows the test to drive the loop as if a user typed "exit", ensuring the loop exits gracefully.

- **Temporary File Cleanup:** The TTS test checks that temporary audio files are deleted after playback, ensuring no resource leaks.

- **Long-Term Memory Truncation:** The long-term memory tests check that long text fields are truncated to a specific length (197 characters plus ellipsis), enforcing memory size limits.

---

## **Configuration and Environment**

- **File System:** Some tests read/write files (e.g., temporary memory JSON, TTS temp files).
- **Environment:** The tests expect the Wheatley package to be installed and importable, with all submodules available.
- **Hardware:** The Arduino interface is initialized, but not actively tested for hardware interaction (would require hardware to be connected for full integration testing).

---

## **Summary of Component Interactions**

1. **Configuration is loaded** using `main.load_config()`.
2. **Assistant components are initialized** via `main.initialize_assistant(config)`, returning all core modules and flags.
3. **Conversation loop** is tested by simulating user input and capturing output.
4. **LLM, TTS, and Conversation Manager** are tested in isolation for their core methods.
5. **Long-term memory** is tested for correct file handling and data truncation.

---

## **Conclusion**

This script provides a comprehensive suite of **unit tests** for the main modules of the Wheatley assistant application. It ensures that configuration, initialization, conversation management, language model interaction, speech synthesis, and memory management all function as expected. The tests are designed to be run automatically and simulate user interaction where necessary, providing a solid foundation for regression testing and future development.
