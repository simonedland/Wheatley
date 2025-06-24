# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\llm\google_agent.py
Certainly! Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script provides a set of helper classes and functions for integrating with **Google Calendar** and for building an **LLM (Large Language Model) agent** that can interact with Google services (primarily Google Calendar) in response to user requests. The agent uses OpenAI's API to interpret user queries and decide which Google Calendar operation to perform, such as listing events or (potentially) creating/deleting events.

---

## **Main Components**

### 1. **GoogleCalendarManager**
**Purpose:**  
A wrapper class for interacting with the Google Calendar API. It handles authentication, calendar listing, and fetching upcoming events.

**Responsibilities:**
- **Configuration Loading:** Reads YAML configuration files for settings and secrets.
- **Authentication:** Loads OAuth2 credentials from a token file (`token.json`) and uses them to authenticate with Google Calendar.
- **Calendar Management:**
  - **list_calendars:** Lists all calendars, skipping those specified in the config.
  - **get_upcoming_events:** Fetches upcoming events from all calendars (except skipped ones) within a specified time window.
  - **print_calendars / print_upcoming_events:** Utility methods to print calendar and event information to the console.

**Notable Logic:**
- Skips calendars based on a config setting.
- Handles API errors gracefully, printing messages and continuing operation.

---

### 2. **GOOGLE_TOOLS**
**Purpose:**  
A list of tool/function definitions that describe possible actions the agent can take with Google Calendar. These are used to inform the LLM about available operations.

**Responsibilities:**
- Defines the schema and description for:
  - Getting upcoming events
  - Creating an event (not implemented)
  - Deleting an event (not implemented)

**Notable Logic:**
- Each tool is described with a JSON schema for its parameters, which is useful for LLM function-calling APIs.

---

### 3. **GoogleAgent**
**Purpose:**  
An agent class that uses an LLM (OpenAI API) to interpret user requests and dispatch them to the appropriate Google Calendar operation.

**Responsibilities:**
- **Configuration Loading:** Loads API keys, LLM model, and other settings from YAML config.
- **OpenAI Integration:** Sets up the OpenAI API key and model.
- **Tool Management:** Holds the list of available tools and passes them to the LLM.
- **LLM Decision Making:**
  - **llm_decide_and_dispatch:** Constructs a prompt for the LLM, asking it to choose the best tool for the user's request. It parses the LLM's response and dispatches the corresponding function.
- **Dispatch Logic:**
  - **dispatch:** Maps the function name chosen by the LLM to the actual method that implements it. Currently, only event listing is implemented; create/delete are placeholders.
- **Calendar Operations:** Wraps the print and event-fetching methods of the `GoogleCalendarManager`.

**Notable Logic:**
- The agent logs the prompt and LLM decision process for debugging.
- Uses OpenAI's function-calling capabilities to let the LLM choose which tool to use.
- Only the "get_google_calendar_events" function is implemented; others are not yet functional.

---

## **Structure and Component Interaction**

- **Configuration:** Both main classes load configuration from a YAML file located at `config/config.yaml` (relative to the script's parent directory). This config includes secrets (API keys) and settings (e.g., calendars to skip).
- **Authentication:** GoogleCalendarManager handles Google OAuth2 authentication, using a token file.
- **LLM Agent:** GoogleAgent initializes both the OpenAI API and a GoogleCalendarManager instance. It uses the LLM to decide which Google tool to use for a given user request, then dispatches the request to the appropriate method.
- **Tool Definitions:** The `GOOGLE_TOOLS` list is used both for LLM prompting and for mapping LLM decisions to actual Python methods.

---

## **External Dependencies & APIs**

- **Google Calendar API:**  
  - `googleapiclient.discovery` and `google.oauth2.credentials` for API access and authentication.
- **OpenAI API:**  
  - For LLM-based decision making.
- **PyYAML:**  
  - For configuration file parsing.
- **Standard Libraries:**  
  - `os`, `json`, `datetime`, etc.

**Configuration Requirements:**
- A YAML config file at `config/config.yaml` with at least:
  - `secrets` (including `openai_api_key`)
  - `skip_calendars` (optional)
  - `llm` (including `model`)
- A Google OAuth2 token at `config/token.json`.

---

## **Notable Algorithms & Logic**

- **LLM Tool Selection:**  
  The agent constructs a system prompt listing available tools and asks the LLM to choose the best tool for the user's request. The LLM's response is parsed to determine which function to call. This is a common pattern for LLM "function calling" or "tool use" workflows.

- **Event Aggregation:**  
  When fetching upcoming events, the manager iterates over all calendars, collects events for each, and organizes them by calendar summary.

- **Error Handling:**  
  The code is robust to API errors, printing messages and skipping problematic calendars or events.

---

## **Summary Table**

| Component                | Purpose/Responsibility                                                                 |
|--------------------------|---------------------------------------------------------------------------------------|
| GoogleCalendarManager    | Handles Google Calendar API authentication, calendar listing, and event retrieval     |
| GOOGLE_TOOLS             | Defines available Google Calendar operations for the LLM agent                        |
| GoogleAgent              | Uses LLM to interpret user requests and dispatches to the appropriate calendar method |
| Config File (YAML)       | Stores secrets (API keys), LLM model, and settings                                   |
| Token File (JSON)        | Stores Google OAuth2 credentials                                                     |

---

## **Limitations & Extensibility**

- **Only event listing is implemented.** Creating and deleting events are placeholders.
- **No token refresh logic:** The commented-out code hints at plans for token refreshing, but it's not active.
- **LLM API Usage:** Assumes a function-calling interface for OpenAI's API, which may require specific OpenAI SDK versions or endpoints.

---

## **Conclusion**

This script is a modular foundation for building an LLM-powered assistant that can interact with Google Calendar. It is well-structured for extension (e.g., adding event creation/deletion), and it demonstrates modern patterns for LLM tool use and API integration. Proper configuration and credentials are required for operation. The code is robust to errors and designed for interactive or automated use.

### C:\GIT\Wheatly\Wheatley\Wheatley\llm\llm_client.py
Certainly! Here’s a detailed summary and analysis of the provided Python script, focusing on its **purpose, structure, main classes/functions, dependencies, configuration, and notable logic**.

---

## **Overall Purpose**

This script provides a set of **wrappers and helper classes/functions** for integrating large language models (LLMs, specifically OpenAI’s GPT models) and various external APIs (such as ElevenLabs for text-to-speech, Google Calendar, Spotify, and weather/advice APIs) into a conversational assistant framework. The assistant can interact with users, call external services, synthesize speech, manage reminders/timers, and more.

---

## **Main Components and Structure**

### **1. Imports and Dependencies**

- **External APIs/Libraries:**
  - `openai`: For LLM (GPT) interactions.
  - `elevenlabs` and `playsound`: For text-to-speech (TTS) synthesis and playback.
  - `requests`: For HTTP requests to external APIs (weather, advice, etc.).
  - `yaml`, `json`: For configuration and data serialization.
  - `asyncio`, `time`, `tempfile`, `os`, `logging`: Standard Python utilities.
- **Local/Project Modules:**
  - `google_agent`, `spotify_agent`: For Google Calendar and Spotify integrations.
  - `llm_client_utils`: For utility functions (weather codes, jokes, quotes, etc.).
  - `utils.timing_logger`: For performance logging.
  - `utils.long_term_memory`: For persistent memory storage.

### **2. TextToSpeech Class**

**Purpose:**  
Wraps the ElevenLabs API to generate and play speech from text, using settings from a YAML config file.

**Key Responsibilities:**
- **Configuration Loading:** Reads TTS settings (voice, API key, etc.) from `config.yaml`.
- **Audio Generation:** Calls ElevenLabs API to synthesize speech.
- **Playback:** Writes audio to a temp file and plays it with `playsound`.
- **Runtime Reloading:** Can reload TTS config on demand.

**Notable Logic:**
- Uses a temp directory and cleans up audio files after playback.
- Tracks and logs timing for TTS generation and playback.

### **3. GPTClient Class**

**Purpose:**  
A wrapper for OpenAI’s GPT chat API, tailored for the assistant (“Wheatley”).

**Key Responsibilities:**
- **Initialization:** Loads API keys and model name from config.
- **Text Generation:** Sends conversation history to GPT and extracts the assistant’s reply.
- **Animation Selection:** Asks GPT to selectHere’s a thorough summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script acts as a **central integration layer** for a conversational assistant (“Wheatley”), providing:

- Wrappers around LLM (OpenAI GPT) API calls.
- Text-to-speech (TTS) via ElevenLabs.
- Integration with Google Calendar and Spotify.
- Tool invocation and workflow execution for various assistant actions (weather, jokes, reminders, etc.).
- Helper functions for utilities like jokes, quotes, weather, and persistent memory.

It is designed to orchestrate complex, multi-step assistant behaviors by combining LLM outputs, external APIs, and local tools.

---

## **Main Classes and Functions**

### **1. `TextToSpeech`**

**Purpose:**  
Encapsulates ElevenLabs TTS API for generating and playing speech.

**Responsibilities:**
- Loads TTS configuration (voice, model, API key, etc.) from `config.yaml`.
- Generates audio from text using ElevenLabs.
- Plays the audio using `playsound`, managing temporary files.
- Can reload configuration at runtime.

**Notable Logic:**
- Uses a temp directory for audio files, cleans up after playback.
- Logs timing for generation and playback.
- Supports dynamic reloading of voice/personality settings.

---

### **2. `GPTClient`**

**Purpose:**  
Handles all interactions with OpenAI’s GPT models.

**Responsibilities:**
- Loads OpenAI API key and model from config.
- Sends conversation history to GPT and extracts the assistant’s reply.
- Asks GPT to select an animation/mood, using an emotion counter to encourage variety.
- Builds and sends tool invocation requests to GPT, supporting parallel tool calls.
- Tracks and persists emotion usage to encourage diverse responses.

**Notable Logic:**
- Dynamically adjusts tool prompts/context based on emotion usage.
- Handles both standard text and tool-calling workflows.
- Persists emotion usage in a JSON file for continuity.

---

### **3. `Functions`**

**Purpose:**  
Implements the actual logic for the “tools” that GPT can invoke.

**Responsibilities:**
- Initializes sub-agents (Google, Spotify) based on config/service status.
- Executes workflows: iterates over tool calls suggested by GPT, dispatches to the relevant function, and collects results.
- Provides implementations for:
  - Google/Spotify agent calls.
  - Timer and reminder scheduling (with async event queue support).
  - Weather queries (via Open-Meteo API).
  - Jokes, quotes, advice (via utility functions or external APIs).
  - City coordinate lookup.
  - Daily summary (combines calendar, weather, and quote).
  - Personality switching (updates config and TTS settings).
  - Persistent memory (read, write, edit).

**Notable Logic:**
- Uses async scheduling for timers and reminders.
- Supports event queue integration for real-time assistant events.
- Handles fallback and error cases for unavailable services.
- Allows dynamic personality switching by updating config and TTS.

---

### **4. Utility Imports and Functions**

- **From `llm_client_utils`:**  
  Weather code descriptions, joke/quote fetchers, city coordinate lookup, tool builders, config loader.
- **From `utils.timing_logger`:**  
  For performance measurement.
- **From `utils.long_term_memory`:**  
  For persistent assistant memory.

---

## **External Dependencies and APIs**

- **OpenAI GPT API:**  
  For all LLM-based conversation and tool selection.
- **ElevenLabs API:**  
  For text-to-speech synthesis.
- **Google Calendar API:**  
  Via `GoogleCalendarManager` and `GoogleAgent`.
- **Spotify API:**  
  Via `SpotifyAgent`.
- **Open-Meteo API:**  
  For weather data.
- **API Ninjas:**  
  For random advice.
- **Other:**  
  `playsound` for audio playback, `requests` for HTTP, `yaml` and `json` for config/data.

---

## **Configuration Requirements**

- **`config.yaml`:**  
  Must exist in a `config` directory two levels up from this script. Contains:
  - API keys (OpenAI, ElevenLabs, API Ninjas, etc.).
  - TTS settings (voice, model, etc.).
  - Assistant personalities and system messages.
  - Web search settings (optional).
- **Emotion counter JSON:**  
  Used to persist emotion/mood usage for animation selection.
- **Long-term memory JSON:**  
  Used for persistent assistant memory.

---

## **Code Structure and Interactions**

- **Assistant workflow:**
  1. **User input** is processed and sent to `GPTClient`.
  2. **GPTClient** determines if a tool call is needed, or generates a reply.
  3. If tools are invoked, **Functions** executes them (possibly using Google/Spotify agents, weather APIs, etc.).
  4. **TextToSpeech** is used to vocalize summaries or actions.
  5. **Event queue** is used for timers/reminders, integrating with the assistant’s event loop.
  6. **Persistent memory** is managed via utility functions.

- **Modularity:**  
  Each external service is abstracted behind a class or utility, allowing for easier extension and maintenance.

---

## **Notable Algorithms and Logic**

- **Emotion Counter:**  
  Tracks which moods/animations have been used, and biases GPT to select less-used ones for variety.
- **Dynamic Tool Context:**  
  System messages and tool descriptions are dynamically adjusted based on conversation state and emotion usage.
- **Async Scheduling:**  
  Uses asyncio for timers and reminders, posting events to an event queue.
- **Personality Switching:**  
  Updates both system messages and TTS settings on the fly, allowing the assistant to change “character”.

---

## **Summary Table**

| Component      | Purpose/Responsibility                                       | Notable Features/Logic              |
|----------------|-------------------------------------------------------------|-------------------------------------|
| TextToSpeech   | ElevenLabs TTS wrapper, playback, config reload             | Temp file mgmt, timing, personality |
| GPTClient      | OpenAI GPT chat, tool invocation, animation selection       | Emotion counter, dynamic prompts    |
| Functions      | Implements all tool logic (weather, reminders, memory, etc) | Async events, multi-agent support   |
| Utilities      | Weather, jokes, quotes, city lookup, config, memory         | Modular, reusable                   |
| Config         | Stores API keys, TTS, personalities, web search, etc.       | YAML-based, reloadable              |

---

## **Conclusion**

This script is a **modular, extensible integration layer** for a conversational AI assistant. It coordinates LLM interactions, TTS, external APIs, and event scheduling, providing a robust foundation for a voice-enabled, multi-modal assistant. The code is designed for flexibility, with dynamic configuration, personality switching, and support for new tools and APIs.

### C:\GIT\Wheatly\Wheatley\Wheatley\llm\llm_client_utils.py
Certainly! Here’s a **detailed summary** of the provided Python script, covering its purpose, structure, main components, external dependencies, and notable logic.

---

## **Overall Purpose**

This script provides **shared utilities and tool definitions** for an LLM (Large Language Model) client, likely as part of a conversational assistant or chatbot system (possibly named "Wheatley"). It offers utility functions (such as fetching jokes, quotes, and weather info), manages tool definitions for function-calling by the LLM, and loads configuration and service status for dynamic tool availability.

---

## **Structure and Main Components**

### **1. Imports and Constants**

- **Standard Libraries:**  
  - `os`, `yaml`, `datetime`, `requests`: For file handling, configuration, date/time, and HTTP requests.
- **Service Status Import:**  
  - Attempts to import `SERVICE_STATUS` from a sibling module, falling back to a local import if needed.
- **Weather Code Descriptions:**  
  - A dictionary mapping weather codes to human-readable descriptions, used for interpreting weather API responses.

---

### **2. Utility Functions**

#### **a. `_load_config()`**
- **Purpose:** Loads a shared YAML configuration file (`config.yaml`) found in a parent directory.
- **Usage:** Provides API keys and other settings for other functions.

#### **b. `get_joke()`**
- **Purpose:** Fetches a random joke from the [Official Joke API](https://official-joke-api.appspot.com/random_joke).
- **Returns:** A formatted string with the joke setup and punchline.

#### **c. `get_quote()`**
- **Purpose:** Fetches a motivational quote from [API Ninjas](https://api-ninjas.com/api/quotes).
- **Requires:** API key from the loaded config.
- **Returns:** A formatted string with the quote and author, or a fallback if unavailable.

#### **d. `get_city_coordinates(city)`**
- **Purpose:** Retrieves latitude and longitude for a specified city using the API Ninjas city endpoint.
- **Requires:** API key from the loaded config.
- **Returns:** A formatted string with coordinates, or a fallback if city data is missing.

---

### **3. Tool Definitions**

#### **a. `set_animation_tool`**
- **Purpose:** Defines a tool for setting the bot's animation/mood based on emotional context.
- **Structure:** JSON schema for function-calling, listing all allowed animation states.

#### **b. `build_tools()`**
- **Purpose:** Dynamically constructs a list of tool/function definitions (as dictionaries) for the LLM to use.
- **Behavior:**
  - Loads config for web search and other purposes.
  - Defines a set of tools, each as a dictionary with metadata (name, description, parameters).
  - Some tools are:
    - **Web search preview** (with optional user location/context size)
    - **Weather retrieval** (with detailed parameter schema)
    - **Joke/quote/city coordinate fetchers**
    - **Advice retrieval**
    - **Google and Spotify agent delegation** (conditionally included based on service status)
    - **Timer and reminder setting**
    - **Daily summary generation**
    - **Personality switching**
    - **Long-term memory write/edit**
  - **Conditional Tool Inclusion:**  
    - If `SERVICE_STATUS` indicates Google or Spotify services are unavailable, those tools are omitted from the returned list.
- **Returns:** The final list of tool definitions.

---

## **External Dependencies and APIs**

- **YAML Configuration:**  
  - Expects a `config.yaml` file with at least a `secrets` section containing API keys.
- **APIs Used:**
  - **Official Joke API:** For random jokes.
  - **API Ninjas:** For quotes and city coordinates (requires API key).
- **Service Status:**  
  - `SERVICE_STATUS` is used to enable/disable Google and Spotify-related tools at runtime.
- **Requests Library:**  
  - Used for all HTTP API calls.

---

## **Configuration Requirements**

- **Config File:**  
  - Must be located at `../config/config.yaml` relative to this script.
  - Should include:
    - `secrets.api_ninjas_api_key` for quote and city APIs.
    - `web_search` section for web search tool configuration (optional).
- **Service Status:**  
  - `SERVICE_STATUS` dictionary must indicate which external agents (Google, Spotify) are available.

---

## **Notable Algorithms and Logic**

- **Dynamic Tool Construction:**  
  - The `build_tools()` function builds the tool list at runtime, including or excluding tools based on configuration and service status.
- **API Key Management:**  
  - API keys are securely loaded from a YAML config, not hardcoded.
- **Weather Code Mapping:**  
  - Weather codes are mapped to human-readable descriptions for better LLM responses.
- **Function Calling Schema:**  
  - Tools are defined in a JSON schema-like format, suitable for LLM function-calling frameworks (e.g., OpenAI's function calling or similar).
- **Contextual Tool Descriptions:**  
  - Some tool descriptions include dynamic context (e.g., current time, day) to help the LLM provide accurate responses.

---

## **Component Interactions**

- **Utility functions** are called directly by the LLM client or via function-calling when the LLM selects a tool.
- **Tool definitions** are provided to the LLM, which can then "call" these tools by name with specified parameters.
- **Service status** and **configuration** are checked at runtime to ensure only available and properly configured tools are exposed.

---

## **Summary Table**

| Component              | Responsibility                                              |
|------------------------|------------------------------------------------------------|
| `_load_config()`       | Loads YAML config for API keys and settings                |
| `get_joke()`           | Fetches a random joke from an external API                 |
| `get_quote()`          | Fetches a motivational quote (API Ninjas, needs API key)   |
| `get_city_coordinates()` | Gets city latitude/longitude (API Ninjas, needs API key) |
| `set_animation_tool`   | Defines animation/mood tool for the bot                    |
| `build_tools()`        | Dynamically builds the list of available LLM tools         |
| `SERVICE_STATUS`       | Controls tool availability for Google/Spotify agents       |
| `WEATHER_CODE_DESCRIPTIONS` | Maps weather codes to human-readable text             |

---

## **Conclusion**

This script is a **shared utility and tool definition module** for an LLM-based assistant. It provides API-backed utility functions, manages configuration and service status, and dynamically builds a set of function-calling tools for the LLM. Its design allows for flexible, context-aware, and secure integration of external services and agent delegation, supporting a wide range of conversational assistant features.

### C:\GIT\Wheatly\Wheatley\Wheatley\llm\spotify_agent.py
Certainly! Here’s a detailed summary and analysis of the provided `spotify_agent.py` script:

---

## **Overall Purpose**

The script implements an **LLM-powered Spotify agent** that can interpret natural language user requests and map them to Spotify actions. It acts as an intelligent interface between a user (via chat/CLI) and the Spotify API, using an LLM (such as OpenAI’s GPT) to decide which Spotify tool/function to invoke based on the user’s request.

---

## **Main Components**

### 1. **External Dependencies**

- **openai**: For LLM-powered decision-making and function/tool selection.
- **yaml**: For configuration loading.
- **json, os, datetime, typing**: Standard Python libraries for data handling, file I/O, and type hints.
- **spotify_ha_utils.SpotifyHA**: A local or relative module that wraps Spotify API calls and provides high-level Spotify control functions.

### 2. **Configuration**

- Loads configuration from `config/config.yaml` (relative to the script’s parent directory), which must include:
  - OpenAI API key (`secrets.openai_api_key`)
  - LLM model configuration (`llm.model`)
- Requires valid Spotify credentials, handled by `SpotifyHA.get_default()`.

---

## **Main Classes and Functions**

### **A. `SPOTIFY_TOOLS`**

- **Purpose**: Defines a list of tool/function specifications that the LLM can choose from.
- **Structure**: Each tool is a dictionary with:
  - `name`: Function name
  - `description`: What the tool does
  - `parameters`: Expected input parameters (JSON schema)
- **Coverage**: Includes tools for playback control, searching, queue management, device management, and history.

---

### **B. `SpotifyAgent` Class**

#### **Responsibilities:**

- **Configuration Loading**: Loads YAML config for API keys and model selection.
- **Spotify API Wrapper**: Instantiates a `SpotifyHA` object for all Spotify operations.
- **Tool List**: Exposes the list of tools to the LLM.
- **LLM Orchestration**: Uses OpenAI’s API to select and call the appropriate tool based on user input.
- **Dispatching**: Maps tool/function names to actual method calls on the `SpotifyHA` object, handling arguments and formatting responses.

#### **Key Methods:**

1. **`_load_config()`**
   - Loads YAML configuration from a fixed path.

2. **`__init__()`**
   - Loads config, initializes Spotify and OpenAI API keys, sets up the tool list.

3. **`_dispatch(name, arguments)`**
   - Core dispatcher that executes the correct Spotify action based on the tool name and arguments.
   - Handles argument parsing, type casting, and calls the corresponding `SpotifyHA` method.
   - Formats responses for user readability.

4. **`llm_decide_and_dispatch(user_request, arguments=None)`**
   - Prepares a prompt for the LLM, including the available tools and current time.
   - Sends the user request and tool list to the LLM, which returns a function call.
   - Dispatches the selected tool with the provided arguments.
   - Returns the result to the user.

---

### **C. `_pretty(obj)` Function**

- **Purpose**: Nicely formats and prints the results of Spotify actions for the CLI.
- **Logic**: Handles different types of responses (tracks, lists, status messages) and prints them in a human-friendly way.

---

### **D. `__main__` Block**

- **Purpose**: Provides a simple command-line interface (CLI) for interactive use.
- **Logic**: 
  - Instantiates the agent.
  - Repeatedly prompts the user for input.
  - Passes the input to the agent, formats the response, and prints it.
  - Handles interruptions gracefully.

---

## **How Components Interact**

1. **User Input**: User types a natural language request.
2. **LLM Prompting**: The agent constructs a prompt for the LLM, listing all available tools and the user’s request.
3. **LLM Tool Selection**: The LLM picks the most appropriate tool (function) and provides arguments.
4. **Dispatch**: The agent’s `_dispatch` method calls the corresponding Spotify function.
5. **Spotify API**: The `SpotifyHA` object interacts with the Spotify API to perform the action.
6. **Response Formatting**: The result is formatted (via `_pretty`) and shown to the user.

---

## **Notable Algorithms and Logic**

- **LLM-Driven Tool Selection**: The agent leverages the LLM’s function-calling capabilities to map free-form user requests to structured function calls, reducing the need for hand-crafted intent parsing.
- **Dynamic Dispatch**: The `_dispatch` method acts as a router, mapping tool names to concrete Spotify operations, handling argument parsing, and formatting.
- **Queue and Device Management**: The agent can search, queue, and remove tracks, as well as manage playback devices and transfer playback, all via natural language.
- **Market-Specific Logic**: Some operations (like `queue_artist_top_track`) are hardcoded for the Norwegian market (`country="NO"`).

---

## **External APIs and Configuration Requirements**

- **Spotify API**: Accessed via the `SpotifyHA` utility class (not shown here).
- **OpenAI API**: Requires a valid API key for LLM-based function selection.
- **YAML Config File**: Must be present at `config/config.yaml` with the necessary secrets and model info.

---

## **Summary Table**

| Component         | Responsibility                                      | Key Interactions                   |
|-------------------|-----------------------------------------------------|------------------------------------|
| `SPOTIFY_TOOLS`   | Tool definitions for LLM                            | Used in LLM prompt and dispatch    |
| `SpotifyAgent`    | Main logic: config, LLM, dispatch, Spotify control  | Uses `SpotifyHA`, OpenAI API       |
| `_pretty`         | CLI output formatting                               | Formats results for user           |
| CLI (`__main__`)  | User interaction loop                               | Calls agent, prints output         |
| `SpotifyHA`       | Spotify API abstraction (external module)           | Handles all Spotify API calls      |

---

## **Conclusion**

This script is a sophisticated bridge between natural language user requests and the Spotify API, using an LLM to select and invoke the appropriate Spotify function. It is modular, extensible, and designed for both interactive CLI use and as a backend agent for more complex systems. Its core logic centers on LLM-driven function selection, dynamic dispatching, and robust Spotify API integration. Configuration and API keys are required for both Spotify and OpenAI access.

### C:\GIT\Wheatly\Wheatley\Wheatley\llm\spotify_ha_utils.py
Certainly! Here’s a detailed summary and analysis of the provided `spotify_ha_utils.py` Python script:

---

## **Overall Purpose**

The script defines a utility module for interacting with the Spotify Web API, focusing on playback and queue management. It wraps the [Spotipy](https://spotipy.readthedocs.io/) library in a class (`SpotifyHA`) that provides high-level, user-friendly methods for controlling playback, searching, queueing, and removing tracks, as well as a CLI demo with optional rich formatting. It is designed for both scripting and interactive command-line use, with features that make it suitable for home automation or personal Spotify control.

---

## **Main Components**

### **1. Configuration Loader**
- **Functionality:** Loads Spotify API credentials and configuration from a YAML file (default: `config/config.yaml`).
- **Details:** Looks for a `secrets` section containing `spotify_client_id` and `spotify_client_secret`.

### **2. `SpotifyHA` Class**
**Purpose:**  
A compact, object-oriented wrapper around Spotipy, focused on queue and playback operations.

#### **Key Responsibilities:**
- **Authentication:** Handles OAuth2 authentication using credentials from the config file.
- **Playback Control:** Play, pause, skip, transfer playback, and toggle play/pause.
- **Queue Management:** Add, search, and remove tracks from the playback queue.
- **Device Management:** List and select active playback devices.
- **Track/Artist/Album Search:** Search for tracks, albums, and artists, and queue or play them.
- **Rich CLI Demo:** Optionally display queue and ETA information in a formatted table using Rich.
- **Utility Functions:** Flatten track data, format durations, and select the best artist match.

#### **Notable Methods:**
- **`__init__`**: Initializes the Spotify client with proper authentication.
- **`get_default`**: Singleton pattern for a default instance.
- **`_flat`**: Flattens Spotify track objects for easier display and manipulation.
- **`_ms_to_mmss`**: Converts milliseconds to a human-readable time string.
- **Playback Methods:** `play`, `pause`, `skip_next`, `toggle_play_pause`, `transfer_playback`, `start_playback`.
- **Queue Methods:** `get_queue`, `add_to_queue`, `remove_from_queue` (precise removal by position), `_queue_wait_times` (calculate ETA for each track in the queue).
- **Search Methods:** `search_tracks`, `search_and_queue_track` (find and queue a track by query), `artist_top_track` (auto-pick top track for an artist), `get_recently_played`.
- **Album Playback:** `play_album_by_name` (search and play an album by name and optional artist).
- **CLI Demo:** `demo` (queues a random top track from an artist and displays the queue with ETA, using Rich if available).

---

## **Structure & Interactions**

- **Configuration:**  
  On initialization, the class loads API credentials from a YAML file. If authentication fails, it prints an error and raises the exception.

- **Spotipy Integration:**  
  All Spotify API calls are made through a Spotipy client, which is authenticated with the loaded credentials.

- **Queue Handling:**  
  The script provides both simple and advanced queue management, including:
  - Adding tracks with optional verification.
  - Removing tracks at a specific position by skipping ahead and re-queuing tracks that were ahead of the removed one (to maintain queue order).
  - Calculating and displaying ETA for each track in the queue.

- **Search & Playback:**  
  The class can search for tracks, albums, and artists, and can automatically pick the best artist match based on the query or popularity.

- **CLI Demo:**  
  If the `rich` library is installed, the demo displays the queue in a visually appealing table with ETA for each track. Otherwise, it falls back to plain text output.

---

## **External Dependencies**

- **[Spotipy](https://spotipy.readthedocs.io/):**  
  For all Spotify Web API interactions (required).

- **[PyYAML](https://pyyaml.org/):**  
  For loading configuration from YAML files (required).

- **[Rich](https://rich.readthedocs.io/):**  
  For optional pretty CLI output (optional, gracefully degrades if not installed).

---

## **Configuration Requirements**

- **YAML Config File:**  
  Expects a YAML file (default: `config/config.yaml`) with a `secrets` section containing:
  - `spotify_client_id`
  - `spotify_client_secret`
- **Redirect URI:**  
  Defaults to `http://127.0.0.1:5000/callback` but can be customized.

---

## **Notable Algorithms & Logic**

### **1. Precise Queue Removal**
- **Problem:** Spotify’s API does not support removing arbitrary tracks from the queue.
- **Solution:** The script removes a track at a given position by:
  - Skipping ahead to the target track (using `skip_next`).
  - Skipping the target track.
  - Re-adding all tracks that were ahead of the removed track, in reverse order, to preserve queue order.
- **Purpose:** Allows for precise queue manipulation not natively supported by Spotify.

### **2. Queue ETA Calculation**
- **Logic:**  
  Calculates the time (ETA) until each track in the queue will play, based on the current playback position and each track’s duration.
- **Purpose:** Enables the CLI demo to show when each queued track will play.

### **3. Artist Auto-Selection**
- **Logic:**  
  When searching for an artist, if there are multiple matches, it prefers an exact name match (case-insensitive), otherwise picks the most popular artist (by followers).
- **Purpose:** Increases reliability of artist-based actions.

### **4. Search and Queue**
- **Logic:**  
  Searches for tracks matching a query, picks the first (or a random) result, and queues it, verifying that it was successfully added.
- **Purpose:** Simplifies the process of finding and queuing tracks via free-text search.

---

## **Script Entry Point**

- If run as a script, it creates a default `SpotifyHA` instance and runs the demo for the artist "Kaizers Orchestra".

---

## **Summary Table**

| Component         | Purpose/Responsibility                                       |
|-------------------|-------------------------------------------------------------|
| Config Loader     | Loads Spotify API credentials from YAML                      |
| SpotifyHA Class   | High-level Spotify API wrapper for playback/queue/search     |
| Playback Methods  | Play, pause, skip, transfer playback                        |
| Queue Methods     | Add, remove, list, and ETA calculation for queue            |
| Search Methods    | Search and queue tracks, albums, and artists                |
| CLI Demo          | Pretty queue/ETA display using Rich (optional)              |
| External Deps     | spotipy, pyyaml, (optional) rich                            |

---

## **Conclusion**

This script is a robust, user-friendly utility for controlling Spotify playback and queue from Python, with advanced features like precise queue manipulation, artist/album/track search, and a rich CLI demo. It is well-suited for automation, scripting, or interactive use, and can be easily extended for custom Spotify control scenarios.
