# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\main.py
Certainly! Here is a detailed summary and analysis of the provided Python script, focusing on its purpose, architecture, main components, and notable logic.

---

## **Overall Purpose**

This script is the main entry point for the "Wheatley assistant," a multimodal AI assistant that integrates:

- **Speech-to-Text (STT):** Converts user speech to text.
- **Large Language Model (LLM):** Handles conversation, tool use, and reply generation (via OpenAI GPT).
- **Text-to-Speech (TTS):** Converts assistant replies to speech.
- **Arduino Hardware Interface:** Controls servos and LEDs on a robot for expressive feedback and animation.

The script orchestrates these subsystems in an asynchronous event loop, enabling interactive, real-time conversation with both text and voice, and providing physical feedback via a robot.

---

## **High-Level Structure**

1. **Imports and Initialization**
   - Standard, third-party, and local modules are imported.
   - Logging and color output are configured.
   - Constants and regular expressions are defined for parsing and concurrency.

2. **Configuration and Setup**
   - Loads configuration from a YAML file.
   - Prints a welcome banner.
   - Initializes all subsystems (LLM, TTS, STT, Arduino).

3. **Event Loop and Async Handling**
   - Defines an asynchronous event loop to process user and system events.
   - Handles both text and voice input, and manages tool/workflow execution.
   - Streams LLM output through TTS and synchronizes with hardware animation.

4. **Subsystem Integration**
   - Each subsystem (STT, TTS, LLM, Arduino) is initialized and connected.
   - The assistant can pause/resume listening, play speech, and trigger hardware animations.

5. **Main Function**
   - Sets up everything, runs a warm-up interaction, and enters the main async loop.

---

## **Main Classes and Functions**

### **1. Configuration and Initialization**

- **`load_config()`**: Loads YAML configuration (API keys, feature flags, model IDs, etc.).
- **`initialize_assistant()`**: Initializes all core components based on config and feature flags.
  - Builds the conversation manager and LLM client.
  - Sets up STT/TTS engines if enabled.
  - Detects and initializes Arduino hardware (with dry-run fallback).

### **2. Event Representation**

- **`Event` dataclass**: Represents any event in the system (user input, timer, reminder, etc.), with source, payload, metadata, and timestamp.

### **3. Asynchronous Event Handling**

- **`user_input_producer()`**: Async coroutine that reads user text input and pushes it as events into an async queue, respecting an "input allowed" event (to prevent overlap with TTS playback).
- **`get_event()`**: Retrieves and normalizes events from the queue.
- **`print_event()`**: Prints events for debugging.

### **4. Conversation and Workflow Management**

- **`process_event()`**: Updates conversation history based on events, and detects exit commands.
- **`run_tool_workflow()`**: Asks the LLM for a workflow (sequence of tool calls), executes them, and adds results to the conversation.
  - **`_fetch_workflow()`**: Gets a workflow from GPT, with retries.
  - **`_inject_context_from_search()`**: Adds web search results to conversation context.
  - **`_refresh_long_term_memory()`**: Updates conversation with long-term memory.
  - **`_execute_workflow()`**: Executes workflow steps and records results.

### **5. Assistant Reply and Streaming**

- **`generate_assistant_reply()`**: Gets a text reply and animation from the LLM, updates conversation, and returns them.
- **`stream_assistant_reply()`**: Streams LLM-generated sentences to TTS, plays them as audio, and synchronizes with animation.
  - Uses a producer-consumer pattern with thread pools for TTS generation and playback.
  - Ensures sentences are played in order and allows for concurrent TTS generation.

#### **Streaming Internals**

- **`_StreamContext` dataclass**: Holds queues, thread pools, and state for streaming.
- **`_sentence_producer()`**: Streams sentences from the LLM, launches TTS jobs, and pushes them to a queue.
- **`_tts_job()` / `_fetch_tts_clip()`**: Generates TTS audio for each sentence, with retry/backoff logic for robustness.
- **`_sequencer()`**: Ensures audio clips are played in the correct order.
- **`_playback_worker()`**: Plays audio clips in a separate thread.

### **6. TTS and Follow-up Handling**

- **`handle_tts_and_follow_up()`**: Plays TTS audio and, if input was by voice, listens for a quick follow-up without requiring the hotword.
- **`handle_follow_up_after_stream()`**: Similar, but used after streaming playback.

### **7. Hardware Animation**

- **`_handle_animation()`**: Gets an animation suggestion from the LLM and sends it to the Arduino interface.

### **8. Main Async Loop**

- **`async_conversation_loop()`**: The core event loop:
  - Waits for events (user/system).
  - Processes events and updates conversation.
  - Runs tool workflows if needed.
  - Streams or prints assistant replies.
  - Handles hardware animation.
  - Manages input gating and follow-up logic.
  - Cleans up on exit.

### **9. Main Function**

- **`main()`**: CLI entry point.
  - Loads config, sets up logging and features.
  - Initializes all subsystems.
  - Runs a warm-up interaction.
  - Starts the async conversation loop.
  - Handles shutdown and cleanup.

---

## **External Dependencies and APIs**

- **YAML**: For configuration.
- **OpenAI API**: For LLM (GPT) interaction.
- **ElevenLabs API**: For advanced TTS.
- **Colorama**: For colored terminal output.
- **Requests**: For HTTP requests (TTS API).
- **PySerial**: For Arduino serial communication (via `hardware.arduino_interface`).
- **Custom Local Modules**: For hardware, LLM, TTS, STT, and utility logic.

**Configuration Requirements:**
- `config/config.yaml` must exist and contain API keys, model IDs, and feature flags.
- OpenAI and ElevenLabs API keys must be valid.
- Arduino must be connected (or dry-run mode will be used).

---

## **Notable Algorithms and Logic**

### **1. Asynchronous Event Loop**
- Uses `asyncio` for concurrency.
- User input and hotword detection are run as background tasks.
- An event queue is used to decouple input, processing, and output.

### **2. Streaming TTS Pipeline**
- LLM output is split into sentences and streamed.
- TTS jobs are launched as soon as sentences are available, using thread pools for concurrency.
- Audio clips are played in order, even if TTS jobs complete out of order.
- Playback is handled in a dedicated thread to avoid blocking the event loop.

### **3. Robustness and Error Handling**
- Retries and exponential backoff are used for TTS API calls.
- Dry-run mode for Arduino if hardware is not available.
- Logging is used extensively for debugging and timing.

### **4. Input Gating**
- User input is blocked while TTS is playing, to prevent overlap.
- After TTS, if the last input was voice, a quick follow-up is allowed without the hotword.

### **5. Tool/Workflow Execution**
- The LLM can return a workflow (sequence of tool calls).
- These are executed and their results are injected back into the conversation.

---

## **Component Interaction**

- **User Input (Text/Voice) → Event Queue → Event Loop**
- **Event Loop**:
  - Updates conversation.
  - May trigger tool workflows.
  - Requests LLM reply (text + animation).
  - Streams reply through TTS and plays audio.
  - Sends animation commands to Arduino.
  - Manages input gating and follow-up.
- **STT/TTS**: Can be enabled/disabled via config and runtime checks.
- **Arduino**: Receives animation commands in sync with assistant replies.

---

## **Summary Table**

| Component         | Responsibility                                      |
|-------------------|----------------------------------------------------|
| Config Loader     | Loads YAML config, API keys, feature flags          |
| ConversationMgr   | Tracks conversation history, memory                 |
| GPTClient         | Handles LLM queries, tool workflows, animations     |
| TTS Engine        | Converts text to speech, streams audio              |
| STT Engine        | Converts speech to text, hotword detection          |
| ArduinoInterface  | Controls robot servos/LEDs for animation            |
| Event Loop        | Orchestrates all input, processing, and output      |
| Streaming Logic   | Concurrent TTS generation and ordered playback      |
| Logging/Timing    | Tracks timings, logs events, exports stats          |

---

## **Conclusion**

This script is a robust, modular, and asynchronous controller for a physical AI assistant. It combines LLM-powered conversation, speech input/output, and real-world feedback via a robot. The code is designed for extensibility, error tolerance, and real-time interaction, with careful management of concurrency and subsystem integration. Configuration is externalized, and the system is ready for both CLI and voice-driven operation, with graceful shutdown and detailed logging.

### C:\GIT\Wheatly\Wheatley\Wheatley\present_timeline.py
Certainly! Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script implements a graphical user interface (GUI) application that visualizes timing and log data from external files. The main goal is to help users analyze the chronological sequence and duration of various functionalities (as a Gantt-like timeline), view summary statistics (average durations), and inspect log events. It is particularly useful for developers or analysts who need to understand the temporal behavior and performance of a system, as well as review associated logs.

---

## **Main Components**

### **1. Helper Functions**

- **`load_timings(path)`**
  - Loads timing data from a JSON file (default: `timings.json`).
  - Returns a list of timing entries, or an empty list if the file does not exist.
  - Each entry is expected to have at least `startTime`, `durationMs`, and `functionality`.

- **`load_logs(path)`**
  - Loads log events from a log file (default: `assistant.log`).
  - Uses a regular expression to parse each line into a timestamp, log level, and message.
  - Returns a list of dictionaries with parsed log entries.

---

### **2. Main GUI Class: `TimelineGUI`**

This is the core of the application, inheriting from `tk.Tk` (the main window in Tkinter).

#### **Initialization and Layout**

- **Window Setup**
  - Sets the window title and size.
  - Initializes file paths for timing and log data.
  - Loads data and creates widgets.

- **Widget Creation (`_make_widgets`)**
  - Top bar with buttons for:
    - Reloading data
    - Opening a timing file
    - Opening a log file
  - Main area uses a tabbed notebook (`ttk.Notebook`) with three tabs:
    - **Timeline:** Gantt chart visualization
    - **Time Summary:** Average duration bar chart
    - **Logs:** Text area for log messages

#### **File Pickers**

- **`_pick_timing` and `_pick_log`**
  - Open file dialogs to select new timing or log files.
  - Update the file path and reload all data/views.

#### **Data Loading and Refresh**

- **`_reload_everything`**
  - Loads timing and log data using the helper functions.
  - Updates all three views (timeline, summary, logs).

---

#### **Visualization and Display**

- **Timeline Tab (`_draw_timeline`)**
  - **Purpose:** Draws a Gantt-like horizontal bar chart showing when each functionality started and how long it lasted.
  - **Data Processing:**
    - Filters out zero-duration entries.
    - Converts start times to matplotlib date numbers.
    - Converts durations from seconds to fractions of a day (for matplotlib).
    - Assigns unique colors to each functionality.
  - **Plotting:**
    - Uses `matplotlib` to create a horizontal bar chart.
    - Adds legend, grid, and annotates each bar with its duration in seconds.
    - Embeds the matplotlib figure into the Tkinter tab using `FigureCanvasTkAgg`.
    - Adds a navigation toolbar for pan, zoom, and save.
  - **Interactive Zoom:**
    - Mouse wheel zooms horizontally (time).
    - Shift + wheel zooms vertically (labels).
    - Custom scroll event handler adjusts axis limits accordingly.

- **Time Summary Tab (`_draw_summary`)**
  - **Purpose:** Shows a bar chart of average execution time per functionality.
  - **Data Processing:**
    - Aggregates total duration and count per functionality.
    - Computes averages and sorts them in descending order.
  - **Plotting:**
    - Creates a horizontal bar chart.
    - Annotates each bar with the average duration.
    - Embeds the figure in the Tkinter tab.

- **Logs Tab (`_show_logs`)**
  - **Purpose:** Displays parsed log entries in a text widget.
  - **Formatting:** Each log line shows the timestamp, level, and message.

---

## **External Dependencies**

- **Tkinter**: Standard Python GUI library (no external install needed).
- **Matplotlib**: For plotting charts and embedding them in the GUI.
- **Other Standard Libraries**: `os`, `json`, `datetime`, `collections`, `re`.

**Note:** The script sets the matplotlib backend to `TkAgg` for embedding plots in Tkinter.

---

## **Configuration and File Requirements**

- **Timing File**: JSON file (default: `timings.json`), each entry should have:
  - `startTime` (ISO format string)
  - `durationMs` (milliseconds, as string or number)
  - `functionality` (string label)
- **Log File**: Plain text log (default: `assistant.log`), each line should match:
  - `YYYY-MM-DD HH:MM:SS LEVEL: message`

---

## **Notable Algorithms and Logic**

- **Gantt Chart Width Calculation**: Converts durations from seconds to fractions of a day to match matplotlib’s date axis scale.
- **Color Assignment**: Assigns unique colors to each functionality using a colormap, ensuring visual distinction.
- **Interactive Zoom**: Implements custom mouse wheel zoom logic for both axes, with bounds checking to prevent axis flipping.
- **Bar Annotation**: Each bar in both charts is annotated with its duration or average, improving readability.

---

## **Structure and Component Interaction**

1. **Startup**: When run, the script creates a `TimelineGUI` window.
2. **Data Loading**: On startup or when the user reloads/changes files, timing and log data are loaded and parsed.
3. **Visualization**: Data is visualized in the appropriate tabs using matplotlib, with interactive features.
4. **User Interaction**: Users can zoom, pan, reload, and switch files using the GUI controls.

---

## **Summary**

This script is a self-contained, interactive GUI tool for visualizing and analyzing timing and log data. It combines Tkinter for the interface and matplotlib for plotting, supporting interactive exploration (zoom, pan) and file selection. The code is modular, with clear separation between data loading, GUI layout, and plotting logic. It is designed for users who want to inspect the temporal behavior of a system and its logs in a convenient, graphical manner.

### C:\GIT\Wheatly\Wheatley\Wheatley\puppet.py
Certainly! Here is a detailed summary and analysis of the provided `servo_puppet.py` script:

---

## **Overall Purpose**

This script implements a **graphical user interface (GUI)** for controlling a set of servos and LEDs on a hardware platform called **OpenRB-150 / Core-2**. The GUI allows users to:

- Move and configure individual servos (such as eyelids, lens, eyeX, eyeY, handles, etc.)
- Adjust servo parameters (angle, velocity, idle band, interval)
- Control RGB LEDs
- Save and apply servo/LED presets (called "animations")
- Monitor real-time feedback from the hardware (actual servo angles)
- Communicate with the hardware via a serial port

The target audience is likely developers, engineers, or animatronics hobbyists working with the OpenRB-150/Core-2 platform.

---

## **Main Classes and Functions**

### **1. SerialBackend**

**Purpose:**  
A thin wrapper around the `pyserial` library for asynchronous serial communication with the hardware.

**Responsibilities:**
- Open and close the serial port.
- Spawn a background thread to read incoming serial data and queue it.
- Provide a method to send commands to the hardware.
- Maintain thread-safe queues for received (rx_q) and transmitted (tx_q) messages.

**Key Methods:**
- `open()`: Opens the serial port and starts the reader thread.
- `_reader()`: Continuously reads lines from the serial port and puts them in the receive queue.
- `send(txt)`: Sends a command string to the hardware.
- `close()`: Closes the serial port and stops the reader thread.

---

### **2. PuppetGUI (inherits from tkinter.Tk)**

**Purpose:**  
The main GUI window for servo and LED control.

**Responsibilities:**
- Layout and manage all GUI widgets (servo controls, LED controls, log area, preset bar).
- Handle user interactions (slider movements, button clicks, preset saving/applying).
- Parse and display feedback from the hardware (e.g., actual servo positions).
- Maintain current configuration state and synchronize it with the hardware.

**Key Methods:**
- `__init__()`: Initializes the GUI, loads presets, sets up the layout, and starts the event loop.
- `_layout()`: Constructs the main GUI layout, including servo rows, LED controls, preset bar, and log area.
- `_servo_row()`: Adds a row of widgets for each servo (slider, velocity, idle, interval, move/cfg buttons, and feedback canvas).
- `_draw_band()`: Draws the servo slider bar, idle band, ticks, and a red dot representing the actual hardware angle.
- `_led_row()`, `_rgb()`, `_pick_color()`, `_send_led()`, `_send_mic_led()`: Handle LED controls and color picking.
- `_preset_bar()`, `_save_preset()`, `_apply_preset()`: Manage saving, loading, and applying servo/LED presets.
- `_send_move()`, `_send_cfg_one()`, `_send_all()`: Send commands to move/configure servos or send all settings at once.
- `_parse_servo_config_line()`, `_parse_move_line()`: Parse incoming serial messages to update servo limits and actual angles.
- `_pump()`: Periodically processes serial queues, updates the log, and refreshes the GUI.

---

### **3. Main Functionality**

- **auto_port()**: Attempts to auto-detect the serial port by scanning for USB/CP210 devices.
- **main()**: Parses command-line arguments, initializes the serial backend and GUI, and starts the main event loop.

---

## **Structure and Component Interaction**

- **Startup**:  
  The script parses command-line arguments (serial port, baud rate, dry-run mode). It attempts to auto-detect the serial port if not provided.

- **Serial Communication**:  
  The `SerialBackend` manages all serial I/O. It queues incoming messages for the GUI to process and sends outgoing commands from the GUI.

- **GUI Layout**:  
  The `PuppetGUI` creates a row for each servo, each with a slider (for angle), entry boxes (velocity, idle, interval), and buttons (move, configure). It also provides controls for RGB LEDs and a preset bar for saving/loading configurations.

- **Real-Time Feedback**:  
  The GUI displays a red dot on each slider to show the actual servo angle as reported by the hardware, updating in real-time as messages are received.

- **Presets**:  
  Presets (animations) are saved as JSON files and can be applied to quickly set all servos and LEDs to stored configurations.

- **Event Loop**:  
  The `_pump()` method is scheduled periodically to process serial queues, update the log, and refresh GUI elements (like the red dot).

---

## **External Dependencies**

- **Python Standard Library**:
  - `argparse`, `json`, `queue`, `re`, `sys`, `threading`, `time`
  - `tkinter` and `tkinter.ttk` for GUI

- **Third-Party**:
  - `pyserial` (optional, for serial communication)
  - `serial.tools.list_ports` for auto-detecting serial ports

- **Configuration/Files**:
  - Presets are stored in a local JSON file (`animations.json`).

---

## **Notable Algorithms and Logic**

- **Servo Feedback Visualization**:  
  Each servo row includes a custom canvas that visually represents the slider's range, the idle band, and the actual position (red dot) as reported by the hardware. This provides immediate visual feedback to the user.

- **Preset Factorization**:  
  Presets store servo positions as normalized factors (0.0–1.0) relative to each servo's min/max range. When applying a preset, these factors are converted back to absolute angles based on the current hardware limits. This makes presets robust to hardware changes.

- **Serial Parsing**:  
  The script parses incoming lines for two main types of feedback:
    - Servo configuration lines (to update min/max limits and enable controls)
    - Servo move/angle feedback (to update the red dot on the slider)

- **Thread-Safe Queuing**:  
  All serial I/O is handled via thread-safe queues to avoid blocking the GUI thread.

- **Dry-Run Mode**:  
  If no serial port is found or specified, the script can run in a "dry-run" mode for GUI testing without hardware.

---

## **Configuration Requirements**

- **Hardware**:  
  OpenRB-150 / Core-2 with servos and LEDs connected, and firmware that understands the command protocol used here.

- **Software**:  
  - Python 3.x
  - `pyserial` installed (for hardware communication)
  - `tkinter` available (for GUI)

- **Presets**:  
  - Presets are saved in `animations.json` in the script's directory.

- **Command-Line Options**:
  - `-p` or `--port`: Serial port (auto-detected if omitted)
  - `-b` or `--baud`: Baud rate (default 115200)
  - `--dry-run`: Run without hardware

---

## **Summary Table**

| Component         | Responsibility                                             |
|-------------------|-----------------------------------------------------------|
| SerialBackend     | Serial comms, background reading, thread-safe queues      |
| PuppetGUI         | Main GUI, servo/LED controls, feedback, presets           |
| auto_port         | Serial port auto-detection                                |
| main              | CLI parsing, app startup, event loop                      |
| animations.json   | Preset storage                                            |

---

## **Notable Features**

- **Live Hardware Feedback**:  
  Red dot on sliders shows actual servo angle as reported by hardware.

- **Flexible Presets**:  
  Presets are normalized and robust to hardware range changes.

- **User-Friendly GUI**:  
  All controls are accessible via a single window, with real-time logging.

- **Extensible**:  
  New servos or features can be added by extending the `SERVO_NAMES` and related logic.

---

## **Conclusion**

This script is a comprehensive and user-friendly GUI tool for controlling and configuring a multi-servo animatronic system via serial communication. It is designed for both real hardware operation and offline/dry-run testing, and supports advanced features like live feedback, robust presets, and LED control. The code is modular, with clear separation between GUI, serial communication, and configuration logic.

### C:\GIT\Wheatly\Wheatley\Wheatley\service_auth.py
Certainly! Here’s a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script provides **authentication helpers** for various external services used by a project named "Wheatley". Its main goal is to verify that the application can successfully authenticate with services like Google, Spotify, OpenAI, and ElevenLabs, and to report the status of these authentications. It also manages service-specific agent instances for Google and Spotify.

---

## **Main Components**

### **Global Variables**

- **SERVICE_STATUS**: A dictionary tracking the authentication status (`True`/`False`) for each service.
- **GOOGLE_AGENT**: Holds an authenticated `GoogleAgent` instance if available, otherwise `None`.
- **SPOTIFY_AGENT**: Holds an authenticated `SpotifyAgent` instance if available, otherwise `None`.

---

### **Functions**

#### **1. _load_config()**

- **Purpose**: Loads configuration data from a YAML file located at `config/config.yaml` relative to the script’s directory.
- **Responsibility**: Reads and parses the YAML file, returning its contents as a dictionary.
- **Interaction**: Used by other functions to retrieve API keys and secrets for authentication.

#### **2. _check_openai(api_key)**

- **Purpose**: Verifies if the provided OpenAI API key is valid.
- **Responsibility**: 
  - Handles both new and old versions of the OpenAI Python library.
  - Attempts a simple API call (`models.list()` or `Model.list()`) to confirm authentication.
- **Interaction**: Called within `authenticate_services()` to check OpenAI credentials.

#### **3. _check_elevenlabs(api_key)**

- **Purpose**: Verifies if the provided ElevenLabs API key is valid.
- **Responsibility**: 
  - Instantiates an `ElevenLabs` client and attempts a simple API call (`voices.get_all()`).
- **Interaction**: Called within `authenticate_services()` to check ElevenLabs credentials.

#### **4. authenticate_services()**

- **Purpose**: The main function that attempts to authenticate with all supported external services.
- **Responsibilities**:
  - Loads configuration and secrets.
  - Tries to authenticate with Google (via `GoogleAgent`), Spotify (via `SpotifyAgent`), OpenAI, and ElevenLabs.
  - Prints colored status messages (using `colorama`) for each service.
  - Updates global agent variables and the `SERVICE_STATUS` dictionary.
  - Returns a dictionary of service authentication statuses.
- **Interaction**: Central orchestrator that uses all other helpers and manages global state.

---

### **Classes and External Agents**

- **GoogleAgent** and **SpotifyAgent**: Imported from local modules. These are wrappers or clients for interacting with Google and Spotify APIs, respectively. Their instantiation and simple API calls (like listing calendars or getting current playback) serve as authentication checks.
- **openai**: The official OpenAI Python library, used for LLM (Large Language Model) API access.
- **ElevenLabs**: A client for the ElevenLabs API, which provides voice and audio services.

---

## **Structure and Flow**

1. **Imports and Setup**: Handles optional imports for OpenAI and ElevenLabs, and imports agent classes for Google and Spotify.
2. **Global State**: Prepares global variables to track authentication and agent instances.
3. **Configuration Loading**: `_load_config()` reads secrets and settings from a YAML file.
4. **Authentication Checks**: Helper functions `_check_openai()` and `_check_elevenlabs()` encapsulate the logic for verifying API keys.
5. **Main Authentication Routine**: `authenticate_services()`:
   - Loads configuration.
   - Attempts to instantiate and verify each service.
   - Prints colored feedback for each service.
   - Updates global status and agent variables.
   - Returns a summary dictionary.

---

## **External Dependencies**

- **openai**: For OpenAI API access (optional).
- **elevenlabs**: For ElevenLabs API access (optional).
- **colorama**: For colored terminal output (required).
- **yaml**: For parsing the YAML configuration file (required).
- **GoogleAgent** and **SpotifyAgent**: Local modules/classes for Google and Spotify API access.

---

## **Configuration Requirements**

- **YAML Config File**: Expects a `config/config.yaml` file with a `secrets` section containing at least:
  - `openai_api_key`
  - `elevenlabs_api_key`
  - (Google and Spotify credentials are likely handled internally by their agents.)

---

## **Notable Logic and Algorithms**

- **Dynamic Import Handling**: The script gracefully handles missing optional dependencies, allowing it to run even if some libraries are not installed (e.g., during documentation builds).
- **Version Compatibility**: The OpenAI authentication check supports both new and old versions of the `openai` library.
- **Colored Output**: Uses `colorama` to print clear, colored status messages for each service.
- **Global State Management**: Updates global agent instances and status dictionary for use elsewhere in the application.
- **Error Handling**: Catches exceptions during authentication attempts, ensuring that a failure in one service does not prevent checks for others.

---

## **Component Interaction**

- **authenticate_services()** is the entry point, calling:
  - `_load_config()` for secrets.
  - Instantiating and verifying `GoogleAgent` and `SpotifyAgent`.
  - Calling `_check_openai()` and `_check_elevenlabs()` with the relevant API keys.
  - Updating global variables and printing results.

---

## **Summary**

This script is a robust, modular authentication helper for a multi-service Python application. It centralizes the logic for verifying access to key external APIs, provides clear feedback, and manages agent instances for further use. Its design allows for flexible deployment, optional dependencies, and easy integration into larger systems.

### C:\GIT\Wheatly\Wheatley\Wheatley\test.py
Certainly! Here’s a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script provides **unit tests** for two main functionalities of an assistant application:

1. **LLM (Large Language Model) interaction** – specifically, testing the ability to generate text responses using a GPT-based client.
2. **TTS (Text-to-Speech) functionality** – specifically, testing the generation and playback of speech from text, and ensuring temporary audio files are cleaned up.

The script is designed to be run as a standalone test suite, using Python’s `unittest` framework.

---

## **Main Classes and Functions**

### 1. **ColorfulTestCase (inherits from unittest.TestCase)**

- **Purpose:**  
  Acts as a custom base class for all test cases in this script. It currently only wraps standard assertion methods (`assertEqual`, `assertIn`, `assertIsInstance`) under slightly different names (`assert_equal`, etc.), but does not add color or other custom output as the name might suggest.
- **Responsibilities:**  
  - Provides a base for other test classes.
  - Could be extended for custom output formatting (e.g., colored output), though this is not implemented here.

---

### 2. **TestLLMFunctionality (inherits from ColorfulTestCase)**

- **Purpose:**  
  Tests the LLM (GPT-based) client’s ability to generate text responses.
- **Main Function:**  
  - `test_get_text`:  
    - Instantiates a `GPTClient`.
    - Sends a simple conversation prompt (user says "Greet me").
    - Calls the `get_text` method to get a response.
    - Asserts that the result is a non-empty string.
    - Catches and reports exceptions as test failures.
    - Prints progress and results for clarity.

---

### 3. **TestTTSFunctionality (inherits from ColorfulTestCase)**

- **Purpose:**  
  Tests the TTS engine’s ability to generate and play speech, and to clean up temporary audio files.
- **Main Function:**  
  - `test_generate_and_play`:  
    - Instantiates a `TextToSpeechEngine`.
    - Calls `generate_and_play_advanced` with the text "Test TTS".
    - Asserts that no exceptions are raised.
    - After playback, checks the designated temporary directory to ensure no leftover files remain (verifying cleanup).
    - Prints progress and results for clarity.

---

## **Structure and Component Interaction**

- The script is structured as a standard `unittest` test suite:
  - **Imports:**  
    - Standard libraries: `os`, `unittest`.
    - Application modules: `llm.llm_client.GPTClient`, `tts.tts_engine.TextToSpeechEngine`.
  - **Test Classes:**  
    - Inherit from a custom base class, which itself is a subclass of `unittest.TestCase`.
    - Each test class targets a specific assistant subsystem (LLM or TTS).
    - Each test method is responsible for a single, well-defined behavior.
  - **Execution:**  
    - If run as a script, executes all tests with increased verbosity.

- **Interaction:**  
  - The LLM test interacts with the GPT client, simulating a conversation.
  - The TTS test interacts with the TTS engine, generating and playing speech, and then checks the filesystem for cleanup.

---

## **External Dependencies and Configuration**

- **External Modules:**
  - `llm.llm_client.GPTClient`:  
    - Presumably a wrapper around an LLM API (e.g., OpenAI GPT).
    - Requires appropriate configuration (API keys, endpoints, etc.) not shown in this script.
  - `tts.tts_engine.TextToSpeechEngine`:  
    - Presumably a wrapper around a TTS system (could be local or cloud-based).
    - May require additional dependencies (TTS libraries, audio playback utilities, etc.).
- **Filesystem:**  
  - The TTS test expects a `temp` directory two levels above the script’s location, used for temporary audio files.
  - The test asserts that this directory is empty after TTS playback, indicating proper cleanup.

---

## **Notable Algorithms and Logic**

- **Test Logic:**  
  - Both test methods are defensive: they catch exceptions and fail the test with a descriptive message if anything goes wrong.
  - The TTS test includes a **cleanup verification** step: after generating and playing audio, it checks the temp directory to ensure no files remain, which is a good practice for resource management.

- **Assertions:**  
  - The LLM test ensures the response is a non-empty string, which is a minimal but effective check for LLM output.
  - The TTS test ensures that no temporary files are left behind, guarding against resource leaks.

---

## **Configuration Requirements**

- The script assumes:
  - The existence and correct configuration of the `llm` and `tts` modules.
  - Any necessary API keys, credentials, or environment variables for LLM and TTS services are set up.
  - The presence of a `temp` directory at the expected location for temporary audio files.

---

## **Summary Table**

| Component/Class        | Responsibility                                         | Dependencies/Notes                       |
|-----------------------|--------------------------------------------------------|------------------------------------------|
| ColorfulTestCase      | Base test class, wraps assertions                      | Could be extended for colored output     |
| TestLLMFunctionality  | Tests GPTClient LLM response                           | Requires `llm.llm_client.GPTClient`      |
| TestTTSFunctionality  | Tests TTS engine output and temp file cleanup          | Requires `tts.tts_engine.TextToSpeechEngine`, filesystem access |
| GPTClient             | Generates text from conversation (external module)     | LLM API, configuration required          |
| TextToSpeechEngine    | Generates and plays speech from text (external module) | TTS backend, audio playback, temp files  |

---

## **Conclusion**

This script is a **basic but effective unit test suite** for verifying the core functionalities of an assistant application: text generation via LLM and speech synthesis via TTS. It checks both for correct output and for proper resource management (file cleanup). The script relies on external modules for LLM and TTS, which must be properly configured for the tests to run successfully. The code is structured for clarity and maintainability, using standard Python testing practices.
