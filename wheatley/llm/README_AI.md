# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\llm\google_agent.py
Certainly! Here is a detailed summary and analysis of the provided `google_agent.py` script:

---

## **Overall Purpose**

The script is designed to serve as an intelligent agent that interfaces with Google Calendar, using both the Google Calendar API and a Large Language Model (LLM, specifically OpenAI's GPT) to interpret user requests and perform calendar-related actions. It allows users to interact with their Google Calendar in natural language, with the LLM deciding which calendar operation to perform (e.g., list events, create, or delete events), and then executing the appropriate API calls.

---

## **Main Components**

### 1. **GoogleCalendarManager**
A utility class that encapsulates all direct interactions with the Google Calendar API.

#### **Responsibilities:**
- **Authentication:** Handles OAuth2 authentication, including token refresh and interactive login via browser if needed. Tokens are stored and reused from disk.
- **Config Loading:** Loads configuration (such as calendars to skip) from a YAML file.
- **Calendar Operations:**
  - **List Calendars:** Retrieves all accessible calendars, excluding those specified in config.
  - **Get Upcoming Events:** Fetches upcoming events from all calendars for a configurable number of days.
  - **Print Helpers:** Utility methods to print calendar lists and upcoming events in a readable format.

#### **Notable Logic:**
- **Token Management:** Tries to refresh tokens if expired, otherwise falls back to an interactive OAuth flow.
- **Configurable Calendar Skipping:** Reads a list of calendar IDs to skip from a YAML config file.

---

### 2. **GOOGLE_TOOLS**
A list of tool/function schemas that define the interface between the LLM and the available Google Calendar operations.

#### **Responsibilities:**
- **Function Descriptions:** Each entry describes a function (get events, create event, delete event) with its parameters, types, and requirements.
- **LLM Integration:** These schemas are passed to the LLM so it knows what actions it can request the agent to perform.

#### **Notable Logic:**
- **OpenAI Function Calling Format:** Uses OpenAI’s structured tool-calling format, allowing the LLM to return a function call with arguments instead of just text.

---

### 3. **GoogleAgent**
The core agent that bridges user requests, the LLM, and the calendar manager.

#### **Responsibilities:**
- **Initialization:** Loads configuration, sets up the OpenAI API key and model, and instantiates the calendar manager.
- **LLM Interaction:** Sends user queries to the LLM, instructing it to choose and call one of the defined tools/functions.
- **Dispatching:** Receives the LLM's tool call, parses the function name and arguments, and invokes the corresponding method on the calendar manager.
- **Print Helpers:** For direct CLI usage, can print calendars and upcoming events.

#### **Notable Logic:**
- **LLM Tool Selection:** The LLM is prompted to pick exactly one tool and output only a tool call, ensuring deterministic and structured responses.
- **Dispatch Mechanism:** Uses the function name from the LLM’s response to route the call to the appropriate handler.
- **Partial Implementation:** Only the "get events" operation is implemented; "create" and "delete" are placeholders.

---

### 4. **Main Script Block**
If run as a script, creates a `GoogleAgent` and asks it to process a sample request ("What’s on my calendar in the next 7 days?"), then prints the result as formatted JSON.

---

## **External Dependencies**

- **Google API Python Client:** For interacting with Google Calendar (`google-api-python-client`, `google-auth`, `google-auth-oauthlib`).
- **OpenAI Python SDK:** For LLM-powered decision making (`openai`).
- **PyYAML:** For reading configuration files (`yaml`).
- **Standard Libraries:** `json`, `datetime`, `pathlib`, `typing`.

---

## **Configuration Requirements**

- **OAuth Credentials:** Requires a Google OAuth client secret file (`client_secret.json`) in a `config` directory.
- **Token Storage:** OAuth tokens are stored in `token.json` in the same directory.
- **YAML Config:** A `config.yaml` file is expected, containing:
  - `skip_calendars`: List of calendar IDs to ignore.
  - `secrets.openai_api_key`: OpenAI API key.
  - `llm.model`: The OpenAI model to use (e.g., `gpt-4`).

---

## **Notable Algorithms and Logic**

- **OAuth Flow:** Handles token refresh, fallback to interactive login, and persistent storage of tokens.
- **LLM Tool Routing:** Uses OpenAI’s function calling to let the LLM choose and parameterize a tool call, then parses and dispatches this call in Python.
- **Calendar Filtering:** Skips calendars as per configuration, and aggregates events across all visible calendars.
- **Error Handling:** Catches and logs API errors, handles missing files, and deals with expired/invalid tokens.

---

## **Structure and Component Interaction**

1. **Initialization:** On startup, configuration is loaded, and authentication is performed.
2. **User Request:** The user provides a natural language request.
3. **LLM Processing:** The agent sends the request to the LLM, along with the available tool schemas.
4. **Tool Selection:** The LLM responds with a structured tool call (function name and arguments).
5. **Dispatch:** The agent parses the tool call and invokes the corresponding method on the calendar manager.
6. **Result:** The result is returned (and printed, if run as a script).

---

## **Summary Table**

| Component              | Responsibility                                    | Key Methods/Attributes                       |
|------------------------|---------------------------------------------------|----------------------------------------------|
| GoogleCalendarManager  | Google Calendar API interaction, config, auth     | list_calendars, get_upcoming_events, ...     |
| GOOGLE_TOOLS           | LLM tool/function schemas                         | N/A (data structure)                         |
| GoogleAgent            | LLM interaction, tool dispatch, config            | llm_decide_and_dispatch, dispatch, ...       |

---

## **Limitations & TODOs**

- **Partial Implementation:** Only event listing is implemented; event creation and deletion are placeholders.
- **No Error Propagation:** Errors are printed but not always surfaced to the caller.
- **Single-User:** Assumes a single user/config; not multi-tenant.
- **No Webhook/Push:** Only supports polling, not real-time updates.

---

## **Conclusion**

This script is a modular, extensible agent for Google Calendar, leveraging LLMs for natural language understanding and tool selection, and the Google API for execution. It is designed for CLI or backend use, with clear separation between LLM-driven intent parsing and API execution, and is readily extensible for more calendar operations or other Google Workspace APIs.

### C:\GIT\Wheatly\Wheatley\Wheatley\llm\llm_client.py
Here's a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script provides a set of client wrappers and helper functions for an AI assistant system. It integrates with various APIs and services, most notably OpenAI's GPT models (for LLM/chat), ElevenLabs (for text-to-speech), Google Calendar, and others. It exposes a framework for orchestrating LLM-driven workflows, tool/function calling, speech synthesis, and external service integration, all configurable via YAML files.

---

## **Main Components**

### 1. **TextToSpeech Class**

- **Purpose:**  
  Wraps the ElevenLabs API to provide text-to-speech (TTS) capabilities.
- **Responsibilities:**
  - Loads TTS configuration (voice, model, API key) from a YAML config file.
  - Generates audio from text using ElevenLabs.
  - Plays generated audio and handles temporary files.
  - Can reload configuration at runtime.
- **Notable Logic:**  
  Uses `playsound` to play audio, manages temp files, and logs timing for performance monitoring.

---

### 2. **GPTClient Class**

- **Purpose:**  
  Encapsulates all interactions with the OpenAI API for chat and function calling.
- **Responsibilities:**
  - Handles chat completions and streaming responses.
  - Extracts and yields sentences in a streaming fashion, with timing info.
  - Manages emotion/mood selection and tracking (for animation or persona).
  - Suggests workflows (sequences of tool calls) based on the conversation.
  - Updates and persists emotion usage statistics.
- **Notable Logic:**
  - Uses regular expressions to split sentences, with logic to avoid splitting at abbreviations.
  - Maintains a JSON file to track emotion/mood usage for more varied responses.
  - Dynamically injects context about emotion usage into prompts for the LLM.
  - Manipulates the conversation history to guide the LLM's workflow/tool call suggestions.

---

### 3. **Functions Class**

- **Purpose:**  
  Acts as a container and dispatcher for all "tools" (functions) that the LLM can call.
- **Responsibilities:**
  - Registers tool functions using a custom `@tool` decorator.
  - Executes a workflow (list of tool calls) as directed by the LLM, narrating each step using TTS.
  - Provides handlers for a variety of assistant actions, including:
    - Google Calendar and Spotify integration
    - Timers and reminders (with async scheduling)
    - Weather retrieval (via Open-Meteo API)
    - Jokes, quotes, advice (via helper functions or APIs)
    - Long-term memory (read/write/edit JSON files)
    - Personality switching (updates config and TTS settings)
  - Provides utility methods for time parsing, scheduling, and narration.
- **Notable Logic:**
  - Dynamically builds a dispatch table of tool functions using Python's `inspect`.
  - Narrates each tool call using the LLM and TTS for a more interactive experience.
  - Schedules timers and reminders asynchronously, posting events to an event queue.
  - Reads and writes to a long-term memory file for persistent storage.

---

### 4. **Helper Functions and Decorators**

- **@tool Decorator:**  
  Registers a method as a tool callable by the LLM, storing its name for later dispatch.
- **Various Utility Functions:**  
  - For weather, jokes, quotes, city coordinates, advice, etc., often imported from other modules.

---

### 5. **Configuration and External Integration**

- **Config Loading:**  
  Uses YAML config files for API keys, TTS settings, personalities, etc.
- **External APIs:**
  - **OpenAI:** For LLM chat, function calling, and streaming.
  - **ElevenLabs:** For TTS.
  - **Open-Meteo:** For weather data.
  - **API Ninjas:** For advice.
  - **Google Calendar & Spotify:** Via agent classes (imported).
- **File Structure:**  
  Relies on a specific directory layout for config, temp, and memory files.

---

### 6. **Event-Driven Design**

- **Event Queue:**  
  Timers and reminders are scheduled asynchronously and post events to an event queue, likely to be consumed by the assistant's main event loop.
- **Narration:**  
  Each tool call can be narrated by the assistant, using the LLM to generate a short, in-character description, which is then spoken via TTS.

---

## **Structure and Flow**

- **Initialization:**  
  Loads configuration and initializes TTS and LLM clients.
- **Tool Registration:**  
  All tool functions are registered in the `Functions` class via the decorator.
- **Workflow Execution:**  
  The LLM suggests a workflow (a list of tool calls), which is executed by the `Functions` class. Each tool call is narrated, executed, and its result collected.
- **External Service Integration:**  
  Tool functions may call out to Google Calendar, Spotify, weather APIs, or other services as needed.
- **Memory and Personality:**  
  The assistant can read/write long-term memory and switch personalities, updating both LLM prompts and TTS settings.

---

## **External Dependencies**

- **Python Packages:**  
  - `openai`, `requests`, `yaml`, `json`, `re`, `playsound`, `elevenlabs`, `tempfile`, `inspect`, `asyncio`, `datetime`, `logging`
- **Local Modules:**  
  - `google_agent`, `llm_client_utils`, `utils.timing_logger`, `utils.long_term_memory`
- **APIs:**  
  - OpenAI (LLM), ElevenLabs (TTS), Open-Meteo (weather), API Ninjas (advice), Google Calendar, Spotify

---

## **Configuration Requirements**

- **YAML Config File:**  
  - Must include API keys (OpenAI, ElevenLabs, API Ninjas), TTS settings, personalities, etc.
- **File Paths:**  
  - Expects certain files and directories (e.g., `config/config.yaml`, `long_term_memory.json`, `llm/emotion_counter.json`, `temp/` directory).

---

## **Notable Algorithms and Logic**

- **Sentence Streaming:**  
  Efficiently yields sentences from a streaming LLM response, using regex to detect sentence boundaries and skipping abbreviations.
- **Emotion/Mood Tracking:**  
  Tracks and persists the frequency of mood/animation selections to encourage varied responses from the LLM.
- **Dynamic Tool Dispatch:**  
  Uses Python introspection to build a dispatch table of available tools, allowing the LLM to call any registered function by name.
- **Narration Pipeline:**  
  For each tool call, generates a short, in-character narration using the LLM, then speaks it using TTS.
- **Async Event Scheduling:**  
  Uses asyncio to schedule timers and reminders, posting events to an event queue for later handling.

---

## **How Components Interact**

- The **GPTClient** handles all LLM interactions, including streaming, tool call suggestions, and animation/mood selection.
- The **Functions** class receives workflows (tool call sequences) from the LLM, narrates and executes them, and returns results.
- The **TextToSpeech** class is used by Functions (and potentially elsewhere) to speak narration or responses.
- External services (Google, Spotify, weather, advice) are accessed via tool functions, which are invoked as needed by the LLM-driven workflow.
- Configuration and memory are loaded and updated as needed to persist state and settings across runs.

---

## **Summary Table**

| Component          | Purpose                                 | Key Responsibilities                                      |
|--------------------|-----------------------------------------|-----------------------------------------------------------|
| TextToSpeech       | ElevenLabs TTS wrapper                  | Speech synthesis, config reload, audio playback           |
| GPTClient          | OpenAI LLM wrapper                      | Chat, streaming, tool call suggestion, mood tracking      |
| Functions          | Tool dispatcher and executor            | Registers tools, executes workflows, narrates, integrates APIs |
| @tool decorator    | Tool registration                       | Marks methods as callable tools for LLM                   |
| Config/Memory      | Persistent settings and state           | Loads/saves YAML config, JSON memory, emotion stats       |
| External Agents    | Google/Spotify integration              | Calendar/music actions via agent classes                  |

---

## **Conclusion**

This script is a sophisticated integration layer for an LLM-powered assistant, providing a modular, extensible framework for tool-based reasoning, speech synthesis, and multi-service orchestration. It is highly configurable, supports persistent state, and is designed for interactive, event-driven operation with rich narration and personality features.

### C:\GIT\Wheatly\Wheatley\Wheatley\llm\llm_client_utils.py
Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script provides **shared utilities and tool definitions** for an LLM (Large Language Model) client, likely part of a conversational AI assistant system. Its main responsibilities are:

- Defining a set of callable "tools" (functions or actions) that the LLM can use to fulfill user requests.
- Providing utility functions for fetching jokes, quotes, city coordinates, and configuration data.
- Managing tool availability based on external service status.
- Supplying metadata and schemas for each tool so that the LLM can invoke them correctly.

---

## **Main Components**

### 1. **External Dependencies**

- **os**: For file path manipulations.
- **yaml**: For loading configuration from YAML files.
- **datetime**: To get the current date and time.
- **requests**: For making HTTP requests to external APIs.
- **service_auth.SERVICE_STATUS**: For checking the status of external services (Google, Spotify, etc.).

### 2. **Configuration Management**

- **_load_config()**:  
  Loads a shared YAML configuration file (`config.yaml`) located in a parent directory. This config provides secrets (API keys) and other settings used by the tools.

### 3. **Utility Functions**

- **get_joke()**:  
  Fetches a random joke from the [Official Joke API](https://official-joke-api.appspot.com/).

- **get_quote()**:  
  Fetches a motivational quote from [API Ninjas](https://api-ninjas.com/api/quotes), using an API key from the configuration.

- **get_city_coordinates(city)**:  
  Looks up latitude and longitude for a given city using the API Ninjas city endpoint, again using the configured API key.

### 4. **Weather Code Descriptions**

- **WEATHER_CODE_DESCRIPTIONS**:  
  A dictionary mapping weather codes (integers) to human-readable weather descriptions. Used for interpreting weather API responses.

### 5. **Tool Definitions**

- **set_animation_tool**:  
  A list containing a tool definition for setting the bot's animation/mood. It specifies allowed animation states and describes how the bot should select an animation based on context.

- **build_tools()**:  
  The core function that assembles and returns a list of all available tools for the LLM client.  
  - Each tool is defined as a dictionary with metadata: type, name, description, and a JSON schema for parameters.
  - Some tools are simple (like `get_joke`), others are more complex (like `get_weather` or `call_google_agent`).
  - The function dynamically includes or excludes tools based on the `SERVICE_STATUS` dictionary (e.g., Google or Spotify tools are only included if those services are available).
  - The web search tool is configured with user location and context size if available in the config.
  - The function also injects the current date and time into the weather tool's description for contextual awareness.

#### **Notable Tool Definitions**
- **get_weather**: Fetches weather and forecast for given coordinates, with flexible forecast range and unit options.
- **test_function**: A simple function for testing function-calling.
- **get_joke, get_quote, get_city_coordinates**: Call the above utility functions.
- **get_advice**: Placeholder for an advice-fetching tool (not implemented in this script).
- **call_google_agent, call_spotify_agent**: Delegate requests to specialized agents for Google and Spotify services.
- **set_timer, set_reminder**: Schedule events or reminders for the user.
- **daily_summary**: Compiles a daily summary from various sources (implementation not shown).
- **set_personality**: Switches the assistant's personality mode.
- **write_long_term_memory, edit_long_term_memory**: Persist and edit JSON data in long-term memory.

---

## **Structure and Interactions**

- **Configuration** is loaded via `_load_config()` whenever a tool needs secrets or settings.
- **SERVICE_STATUS** is used to dynamically enable/disable tools for Google and Spotify, ensuring the LLM only offers tools that are available.
- **Tool Metadata** is structured to be compatible with function-calling LLMs (e.g., OpenAI's function calling), with JSON schemas for parameters and clear descriptions.
- **APIs**: The script interacts with several external APIs:
  - Official Joke API (no auth)
  - API Ninjas (quotes, city lookup; requires API key)
- **Weather Codes**: The script provides a mapping for interpreting weather API responses (not directly used here, but likely used elsewhere in the system).

---

## **Configuration Requirements**

- **config.yaml**:  
  Must exist in a `config` directory one level above the script.  
  - Should contain a `secrets` section with at least `api_ninjas_api_key`.
  - May contain `web_search` settings (e.g., `user_location`, `search_context_size`).

- **service_auth.py**:  
  Must provide a `SERVICE_STATUS` dictionary indicating which external services are available.

---

## **Notable Logic and Algorithms**

- **Dynamic Tool Availability**:  
  The `build_tools()` function checks `SERVICE_STATUS` to include/exclude tools for Google and Spotify, ensuring that the LLM doesn't offer unavailable services.

- **Contextual Tool Descriptions**:  
  The weather tool's description dynamically includes the current day and time, and provides logic for interpreting user requests about "the weekend" based on the current day.

- **Parameter Schema Enforcement**:  
  Each tool defines a strict JSON schema for its parameters, ensuring that the LLM provides the correct arguments when invoking tools.

- **API Key Management**:  
  API keys are never hardcoded; they're loaded from a secure config file.

---

## **Summary Table**

| Component                  | Purpose/Responsibility                                                                 |
|----------------------------|---------------------------------------------------------------------------------------|
| `_load_config()`           | Loads YAML config with secrets and settings                                           |
| `get_joke()`               | Fetches a random joke from an external API                                           |
| `get_quote()`              | Fetches a motivational quote using API Ninjas                                        |
| `get_city_coordinates()`   | Looks up city coordinates using API Ninjas                                           |
| `WEATHER_CODE_DESCRIPTIONS`| Maps weather codes to human-readable descriptions                                    |
| `set_animation_tool`       | Defines an animation/mood-setting tool for the bot                                   |
| `build_tools()`            | Assembles and returns a list of available tools, with dynamic inclusion/exclusion    |
| `SERVICE_STATUS`           | Dictates which tools are available based on external service status                  |

---

## **Conclusion**

This script is a **tool and utility registry** for an LLM-based assistant, providing both the definitions and implementations for a range of assistant actions. It is designed for extensibility, security (via config), and dynamic adaptability to available services. The script is intended to be imported and used by the main LLM client, which will invoke these tools as needed to fulfill user requests.

### C:\GIT\Wheatly\Wheatley\Wheatley\llm\spotify_agent.py
Certainly! Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script implements a **Spotify agent** that enables users to interact with their Spotify account using natural language. It leverages a **Large Language Model (LLM)** (e.g., OpenAI's GPT) to interpret user requests, select the appropriate Spotify tool/function, and execute playback or account management actions. The agent supports a variety of Spotify operations, such as searching for tracks, managing playback, queueing songs, listing devices, and more.

---

## **Main Components and Structure**

### **1. Tool Definitions (`SPOTIFY_TOOLS`)**

- **Purpose:**  
  Defines a list of Spotify-related "tools" (functions) that the LLM can select from. Each tool is described with a name, description, and expected parameters (using a JSON schema-like format).
- **Examples of tools:**  
  - `search_tracks`: Search for tracks by text.
  - `queue_track_by_name`: Find and queue a song.
  - `get_recently_played`: Show recent listening history.
  - `list_devices`: List available Spotify devices.
  - `transfer_playback`: Switch playback to a device.
  - `play_album_by_name`: Play an album by name.
  - Others: get current track, get queue, toggle play/pause, skip track, queue artist top track, remove queue item.

### **2. Handler Registration (`handles` decorator and `_HANDLER_REGISTRY`)**

- **Purpose:**  
  Provides a decorator (`@handles`) to register handler methods for each tool by name. This allows for dynamic dispatching of tool calls to the correct method.
- **Mechanism:**  
  The decorator adds the handler function to the `_HANDLER_REGISTRY` dictionary, mapping tool names to their corresponding methods.

### **3. `SpotifyAgent` Class**

- **Purpose:**  
  The central class that manages configuration, authentication, LLM interaction, and dispatching tool calls.
- **Key Methods:**
  - `__init__`: Loads configuration, authenticates with Spotify (via a utility class), and sets up the LLM and tool list.
  - `_load_config`: Loads configuration from a YAML file (expects OpenAI API key and LLM model info).
  - `_dispatch`: Looks up and calls the appropriate handler for a given tool name and arguments.
  - `_coerce`: Utility to ensure arguments are in dict form (parsing JSON strings if necessary).
  - **Handlers:**  
    Each tool has a corresponding handler method (decorated with `@handles`). These methods interact with the `SpotifyHA` utility class to perform the actual Spotify API calls.
  - `llm_decide_and_dispatch`:  
    - Constructs a prompt for the LLM, listing all available tools and the current time.
    - Sends the user request (and optional arguments) to the LLM.
    - Expects the LLM to return a function call (tool selection and arguments).
    - Dispatches the call to the appropriate handler.
    - Raises an error if the LLM does not return a function call.

### **4. Utility Functions**

- `_pretty`:  
  Formats and prints the results of Spotify operations in a user-friendly way (for command-line interaction).

### **5. Command-Line Interface (CLI) Section**

- If run as a script, the agent enters a REPL loop, prompting the user for input, passing it to the agent, and pretty-printing the result.

---

## **External Dependencies**

- **openai**:  
  For LLM interaction (OpenAI API key required in config).
- **yaml**:  
  For configuration file parsing.
- **spotify_ha_utils.SpotifyHA**:  
  A utility class (not included here) that wraps Spotify API calls and provides methods like `get_current_track`, `search_tracks`, `queue_track_by_name`, etc.
- **Standard libraries**:  
  `os`, `json`, `datetime`, `typing`.

---

## **Configuration Requirements**

- **YAML config file**:  
  Expected at `config/config.yaml` (relative to the script's parent directory).
  - Must contain:
    - `secrets.openai_api_key`: OpenAI API key.
    - `llm.model`: Model name for the LLM (e.g., `gpt-4`).
- **Spotify authentication**:  
  Handled by `SpotifyHA.get_default()`. The user must be authenticated with Spotify (details abstracted in `SpotifyHA`).

---

## **Notable Algorithms and Logic**

### **LLM Tool Selection and Dispatch**

- The agent constructs a prompt for the LLM, listing all available tools and their descriptions.
- The LLM is instructed to pick **exactly one tool** and respond with a function call (tool name and arguments).
- The agent parses the LLM's response and dispatches the call to the corresponding handler.
- This architecture allows the agent to be **extensible**: new tools can be added by defining their schema and handler.

### **Handler Registration via Decorators**

- The use of a decorator (`@handles`) to register handlers for each tool name is a clean, scalable way to map tool names to methods.

### **Dynamic Argument Coercion**

- Arguments passed to handlers may be dicts or JSON strings; `_coerce` ensures they are always dicts for handler use.

---

## **Component Interactions**

1. **User Input** (via CLI or programmatically).
2. **LLM Prompt Construction**:  
   The agent builds a prompt including the tool list and user request.
3. **LLM Call**:  
   Sends the prompt to the OpenAI API, requesting a function call.
4. **Tool Selection**:  
   The LLM chooses the appropriate tool and provides arguments.
5. **Dispatch**:  
   The agent dispatches the call to the registered handler.
6. **Spotify API Call**:  
   The handler uses `SpotifyHA` to interact with Spotify.
7. **Result Formatting**:  
   The result is formatted and returned (or printed in the CLI).

---

## **Summary Table of Main Tools and Handlers**

| Tool Name              | Handler Method                | Description                                      |
|------------------------|------------------------------|--------------------------------------------------|
| get_current_track      | _get_current_track           | Info about currently playing track                |
| get_queue              | _get_queue                   | Upcoming queue with ETA                          |
| toggle_play_pause      | _toggle_play_pause           | Toggle play/pause                                |
| skip_next_track        | _skip_next_track             | Skip to next track                               |
| search_tracks          | _search_tracks               | Search for tracks                                |
| queue_track_by_name    | _queue_track_by_name         | Find and queue a track                           |
| queue_artist_top_track | _queue_artist_top_track      | Queue top track by artist                        |
| remove_queue_item      | _remove_queue_item           | Remove tracks from queue                         |
| list_devices           | _list_devices                | List Spotify devices                             |
| transfer_playback      | _transfer_playback           | Transfer playback to device                      |
| get_recently_played    | _get_recently_played         | Show recently played tracks                      |
| play_album_by_name     | _play_album_by_name          | Play an album by name                            |

---

## **Extensibility**

- **Adding new tools**:  
  Add a new entry to `SPOTIFY_TOOLS` and define a handler method with the `@handles` decorator.
- **Changing LLM model or API**:  
  Update the config file.

---

## **Summary**

This script provides a robust, extensible agent for controlling Spotify via natural language, using LLM-powered tool selection. It abstracts Spotify API interactions behind a set of tools, each with a handler, and uses a decorator-based registry for dispatch. The agent is designed for both command-line and programmatic use, and is easily configurable and extensible. The separation of tool definitions, handler registration, and LLM interaction makes the codebase maintainable and adaptable to new features or tools.

### C:\GIT\Wheatly\Wheatley\Wheatley\llm\spotify_ha_utils.py
Certainly! Here’s a **detailed summary and analysis** of the provided `spotify_ha_utils.py` script, covering its **purpose, structure, main classes/functions, dependencies, configuration, and notable logic**.

---

## **Overall Purpose**

This script provides a **convenient, object-oriented wrapper** around the [Spotipy](https://spotipy.readthedocs.io/) library for the Spotify Web API, focusing on **queue and playback management**. It includes utilities for searching, queueing, and controlling playback, as well as a CLI demo (with optional [Rich](https://rich.readthedocs.io/) output) that displays the current queue and estimated times until each track plays.

---

## **Main Components**

### **1. Configuration Loader**

- **Function:** `_load_cfg`
- **Responsibility:** Loads configuration (including Spotify API credentials) from a YAML file, typically expected at `../config/config.yaml` relative to the script.
- **Interaction:** Used during initialization for authentication.

---

### **2. Main Class: `SpotifyHA`**

#### **Purpose**
A compact, user-friendly wrapper around Spotipy, focusing on playback, queue, and search operations, with some extra utilities for CLI demonstration and queue management.

#### **Key Responsibilities & Methods**

##### **Construction and Authentication**
- **`__init__`**: Handles OAuth authentication using credentials from the config file. Sets up the Spotipy client.
- **`get_default`**: Singleton pattern for a default instance.

##### **Helpers**
- **`_flat`**: Flattens a Spotify track dictionary to a simplified structure (id, uri, name, artists, album, image, duration).
- **`_ms_to_mmss`**: Converts milliseconds to a human-readable time string.
- **`_fmt_track`**: Formats a track for display.

##### **Playback State and Queue**
- **`get_current_playback`**: Returns current playback state.
- **`get_current_track`**: Returns the currently playing track (optionally simplified).
- **`is_playing`**: Returns whether playback is active.
- **`get_queue`**: Returns the current playback queue (optionally simplified).
- **`_queue_wait_times`**: Returns a list of (track, wait_time) tuples, estimating how long until each track will play.

##### **Device Management**
- **`list_devices`**: Lists available Spotify devices.
- **`get_active_device`**: Returns the currently active device.
- **`_with_device`**: Helper to resolve a device ID, defaulting to the active device.

##### **Playback Control**
- **`play`, `pause`, `skip_next`, `toggle_play_pause`, `transfer_playback`, `start_playback`**: Control playback and device transfer.

##### **Search and Queue**
- **`search_tracks`**: Search for tracks by query.
- **`add_to_queue`**: Adds a track to the queue, with optional verification.
- **`search_and_queue_track`**: Searches for a track and queues it (optionally picking the first or a random result).

##### **Queue Manipulation**
- **`remove_from_queue`**: Removes a track from the queue at a specified position. This is done by skipping tracks and re-queueing those ahead, since the Spotify API does not support direct removal.

##### **Artist and Album Helpers**
- **`_best_artist`**: Picks the best-matching artist from a list, based on query or follower count.
- **`artist_top_track`**: Finds and queues the top track for a given artist, with options for country and random selection.
- **`get_recently_played`**: Returns recently played tracks.
- **`play_album_by_name`**: Searches for an album (optionally by artist) and starts playback of that album.

##### **CLI Demo**
- **`demo`**: Demonstrates queueing a top track by a given artist and displays the queue with ETAs, using Rich if available for pretty output.

---

### **3. CLI Entry Point**

- If run as a script, it creates a default `SpotifyHA` instance and runs the demo for "Kaizers Orchestra".

---

## **External Dependencies**

- **[spotipy](https://spotipy.readthedocs.io/):** Python client for the Spotify Web API (required).
- **[PyYAML](https://pyyaml.org/):** For reading configuration (required).
- **[rich](https://rich.readthedocs.io/):** For pretty CLI output (optional).
- **Spotify Developer Account:** Required for API credentials (client ID/secret).

---

## **Configuration Requirements**

- **YAML Config File:** Expected at `../config/config.yaml` (relative to script), containing at least:
  - `spotify_client_id`
  - `spotify_client_secret`
- **Redirect URI:** Defaults to `http://127.0.0.1:5000/callback`, must be set in your Spotify developer dashboard.

---

## **Notable Algorithms and Logic**

### **Queue Wait Time Calculation**
- The `_queue_wait_times` method estimates the time until each track in the queue will play, by summing the remaining time of the current track and the durations of queued tracks.

### **Precise Queue Removal**
- The `remove_from_queue` method works around the lack of a direct "remove from queue" API by:
  - Skipping forward to the target track.
  - Skipping it (thus removing it from the queue).
  - Re-adding any tracks that were ahead of it, preserving queue order.

### **Artist Selection**
- The `_best_artist` method tries to match the query exactly, otherwise picks the artist with the most followers.

### **Rich CLI Output**
- If Rich is installed, the demo displays a formatted table with track names, artists, and ETAs.

---

## **Component Interactions**

- **Authentication** is handled on initialization, using config loaded by `_load_cfg`.
- **Playback and queue operations** are performed via the Spotipy client (`self._sp`), with helpers for formatting and device management.
- **CLI demo** uses the other methods to queue a track, compute ETAs, and display the results.

---

## **Summary Table**

| Component         | Responsibility                                    | Notable Features                                 |
|-------------------|---------------------------------------------------|--------------------------------------------------|
| `_load_cfg`       | Load YAML config                                  | Expects Spotify credentials                      |
| `SpotifyHA`       | Main OO wrapper for Spotipy                       | Playback, queue, search, artist/album helpers    |
| `demo`            | CLI demonstration of queue/ETA                    | Uses Rich if available                           |
| External deps     | spotipy, yaml, rich (optional)                    | Requires Spotify developer credentials           |
| Notable logic     | Queue ETA, precise queue removal, artist picking  | Workarounds for API limitations                  |

---

## **Conclusion**

This script is a **feature-rich utility for Spotify playback and queue management**, ideal for automation, CLI tools, or integration with smart home systems. It abstracts away much of the Spotipy boilerplate, adds user-friendly helpers, and provides a nice CLI demo for interactive use. The code is modular, extensible, and demonstrates thoughtful workarounds for Spotify API limitations (notably queue removal and artist selection). Configuration is handled via YAML, and the script is ready for both import as a module and standalone CLI use.
