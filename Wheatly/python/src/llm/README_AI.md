# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\google_agent.py
Here’s a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script provides a framework for integrating Google Calendar with an LLM (Large Language Model) agent, such as OpenAI’s GPT. It enables programmatic access to a user’s Google Calendar, allowing the agent to fetch calendar data and, in the future, create or delete events based on natural language instructions. The agent uses configuration files for secrets and settings, and is designed to be extensible for more Google Workspace automation.

---

## **Main Components**

### 1. **GoogleCalendarManager Class**

**Purpose:**  
Encapsulates all interactions with the Google Calendar API, including authentication, listing calendars, and fetching upcoming events.

**Responsibilities:**
- **Configuration Loading:**  
  Loads configuration (YAML) files for secrets and settings, such as which calendars to skip.
- **Authentication:**  
  Handles OAuth2 authentication with Google, using credentials from the config file and a token file for session persistence.
- **Calendar Listing:**  
  Lists all user calendars, filtering out those specified in the configuration.
- **Event Fetching:**  
  Retrieves upcoming events from all calendars (except skipped ones) within a specified time window.
- **User-Friendly Output:**  
  Provides methods to print calendars and events in a readable format.

**Notable Logic:**
- **Token Management:**  
  Checks for an existing token file and uses it for authentication. (Token refresh and interactive login are present but commented out.)
- **Configurable Calendar Skipping:**  
  Reads a list of calendar IDs to skip from the YAML config, allowing users to ignore certain calendars.

---

### 2. **GOOGLE_TOOLS (Function Descriptions)**

**Purpose:**  
Defines a list of tool/function descriptions for the LLM agent, describing what actions can be taken (get events, create event, delete event), their parameters, and usage hints.

**Responsibilities:**
- **LLM Integration:**  
  Provides structured descriptions of available functions so the LLM can decide which to invoke based on user input.
- **Extensibility:**  
  Designed to be easily extended with more Google-related functions.

---

### 3. **GoogleAgent Class**

**Purpose:**  
Acts as an LLM-driven assistant that interprets user requests, decides which Google tool to use (via the LLM), and dispatches the request to the appropriate function.

**Responsibilities:**
- **Configuration Loading:**  
  Loads secrets (including OpenAI API key) and LLM model configuration from YAML.
- **LLM Decision Making:**  
  Constructs a prompt for the LLM, listing available tools and the user’s request, and asks the LLM to select the appropriate tool.
- **Function Dispatch:**  
  Receives the LLM’s decision and arguments, then calls the corresponding method (currently only event fetching is implemented).
- **Calendar Operations:**  
  Delegates calendar-related operations to the `GoogleCalendarManager`.
- **Output:**  
  Prints trace information for debugging and transparency.

**Notable Logic:**
- **Prompt Engineering:**  
  Dynamically builds a system prompt for the LLM, including tool descriptions and current date/time context.
- **LLM Output Handling:**  
  Expects the LLM to return a function call with arguments, then dispatches accordingly.
- **Extensibility:**  
  The dispatch method is designed to be easily extended as more tools are implemented.

---

## **External Dependencies and APIs**

- **Google APIs:**  
  - `googleapiclient`, `google_auth_oauthlib`, `google.oauth2.credentials`: For Google Calendar API access and OAuth2 authentication.
- **OpenAI API:**  
  - `openai`: For LLM-based decision making.
- **YAML:**  
  - `yaml`: For configuration file parsing.
- **Standard Libraries:**  
  - `os`, `json`, `datetime`: For file paths, JSON handling, and date/time operations.

---

## **Configuration Requirements**

- **YAML Config File:**  
  - Located at `config/config.yaml` (relative to the script’s parent directory).
  - Must contain:
    - Google API credentials (`google_client_id`, `google_client_secret`, `project_id`).
    - OpenAI API key.
    - LLM model name.
    - Optional: `skip_calendars` list.
- **Token File:**  
  - Located at `config/token.json`.
  - Stores OAuth2 tokens for Google API access.

---

## **Structure and Component Interaction**

1. **Initialization:**  
   - `GoogleAgent` and `GoogleCalendarManager` both load configuration from YAML.
   - `GoogleCalendarManager` handles Google authentication and API service setup.

2. **User Request Handling:**  
   - User request is passed to `GoogleAgent.llm_decide_and_dispatch`.
   - The agent prompts the LLM with available tools and the user’s request.
   - LLM selects a tool and provides arguments.
   - The agent dispatches the request to the appropriate method (e.g., fetching calendar events).

3. **Calendar Operations:**  
   - All calendar-related actions are handled by `GoogleCalendarManager`.
   - Results can be printed or returned as needed.

---

## **Notable Algorithms and Logic**

- **LLM Tool Selection:**  
  The agent uses prompt engineering to guide the LLM in selecting the correct function/tool for a user’s request, based on structured tool descriptions.
- **Dynamic Dispatch:**  
  The agent parses the LLM’s structured response and dynamically calls the appropriate handler method.
- **Configurable Filtering:**  
  The calendar manager supports skipping specified calendars, making the integration more user-friendly and customizable.

---

## **Unimplemented/Placeholder Features**

- **Event Creation and Deletion:**  
  Function descriptions for creating and deleting events are defined, but the actual implementations are placeholders ("not implemented").
- **Token Refresh and Interactive Login:**  
  Code for refreshing expired tokens and running an OAuth2 flow is present but commented out.

---

## **Summary Table**

| Component                  | Responsibility                                   | Key Methods/Attributes                  |
|----------------------------|--------------------------------------------------|-----------------------------------------|
| GoogleCalendarManager      | Google Calendar API integration                  | `_load_config`, `get_google_credentials`, `list_calendars`, `get_upcoming_events`, `print_calendars`, `print_upcoming_events` |
| GOOGLE_TOOLS               | LLM tool/function descriptions                   | N/A (data structure)                    |
| GoogleAgent                | LLM-driven assistant and dispatcher              | `_load_config`, `llm_decide_and_dispatch`, `dispatch`, `get_google_calendar_events`, `print_calendars`, `print_upcoming_events` |

---

## **Conclusion**

This script is a modular, extensible foundation for building an LLM-powered Google Calendar assistant. It cleanly separates concerns between API integration and LLM-driven orchestration, uses configuration files for secrets and settings, and is designed for easy extension to more Google Workspace automation tasks. The core implemented logic focuses on secure, configurable access to calendar data and LLM-based tool selection, with clear placeholders for future feature expansion.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\llm_client.py
Certainly! Here’s a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script serves as a set of wrappers and helper functions for integrating various AI and assistant-related services into a conversational assistant (possibly named "Wheatley"). It provides interfaces for:

- **Large Language Model (LLM) interactions** (primarily OpenAI GPT models)
- **Text-to-Speech (TTS)** using the ElevenLabs API
- **External tool integrations** (Google Calendar, Spotify, weather, jokes, quotes, advice, etc.)
- **Workflow orchestration** where the LLM can suggest and trigger tool calls
- **Event scheduling** (timers, reminders)
- **Audio playback** for assistant responses

The script is designed to be modular and extensible, facilitating the orchestration of complex assistant behaviors.

---

## **Main Classes and Functions**

### 1. **TextToSpeech**

- **Purpose:** Wraps the ElevenLabs API for TTS, allowing the assistant to synthesize and play speech.
- **Responsibilities:**
  - Loads configuration (API key, voice settings) from a YAML file.
  - Generates audio from text using ElevenLabs.
  - Plays the generated audio and handles temporary file management.
- **Notable Logic:** Uses a temporary file for audio playback and cleans up after playback.

---

### 2. **GPTClient**

- **Purpose:** Encapsulates interactions with the OpenAI GPT API for chat-based tasks.
- **Responsibilities:**
  - Loads API keys and model configuration.
  - Maintains state (e.g., last mood, emotion usage counters).
  - Provides methods to:
    - Get textual responses from GPT.
    - Ask GPT to select an animation/mood, using emotion usage statistics to encourage variety.
    - Get a workflow (list of tool calls) suggested by GPT based on the conversation.
- **Notable Logic:**
  - Tracks and persists emotion usage to a JSON file to influence future animation selections.
  - Dynamically injects context into tool calls for more natural and varied assistant behavior.

---

### 3. **Functions**

- **Purpose:** Implements the actual logic for each tool/function that can be invoked by the assistant, as suggested by the LLM.
- **Responsibilities:**
  - Initializes various agents (Google, Spotify) and loads configuration.
  - Executes a workflow (list of tool calls), dispatching each to the appropriate handler.
  - Handles TTS narration of function execution (in a humorous, concise style).
  - Implements handlers for:
    - Google and Spotify agent calls
    - Timers and reminders (with async scheduling and event queue integration)
    - Weather queries (using Open-Meteo API)
    - Jokes, quotes, advice, city coordinates, and daily summaries
- **Notable Logic:**
  - For reminders and timers, uses asyncio to schedule future events and posts them to an event queue.
  - Parses flexible time formats for reminders (e.g., "7am", "19:30").
  - Weather handler interprets weather codes and provides human-readable summaries.

---

### 4. **Helper Functions and Configuration**

- **_load_config:** Loads YAML configuration from a standard location.
- **Integration with other modules:** Imports various utility functions and agents (GoogleAgent, SpotifyAgent, etc.) from local files or packages.
- **Logging:** Uses Python’s logging module for debug and error reporting.

---

## **External Dependencies and APIs**

- **OpenAI:** For LLM (GPT) chat interactions.
- **ElevenLabs:** For TTS (speech synthesis).
- **Google and Spotify Agents:** For calendar and music control (assumed to be custom modules).
- **Open-Meteo API:** For weather data.
- **API Ninjas:** For advice.
- **playsound:** For audio playback.
- **requests:** For HTTP requests to external APIs.
- **yaml:** For configuration file parsing.

---

## **Configuration Requirements**

- **config.yaml:** Must be present in a `config` directory two levels above the script. Should contain API keys and settings for OpenAI, ElevenLabs, TTS, web search, etc.
- **emotion_counter.json:** Used to persist emotion usage statistics for animation selection.
- **Other agent modules:** Google and Spotify agent modules must be available either in the `llm` package or as local files.

---

## **Code Structure and Component Interaction**

- **Configuration is loaded at startup** and used throughout the script for API keys and feature toggles.
- **GPTClient** is the main interface for LLM interactions, and can suggest tool calls (functions) to execute.
- **Functions** class acts as a dispatcher, executing the tool calls suggested by the LLM and returning results.
- **TextToSpeech** is used by Functions to narrate actions if TTS is enabled.
- **Agents (Google, Spotify, etc.)** are initialized and called as needed.
- **Workflow Execution:** The LLM suggests a sequence of tool calls, which are executed in order, with results collected and returned.
- **Event Scheduling:** Timers and reminders are scheduled asynchronously and post events to a queue for the assistant to handle.

---

## **Notable Algorithms and Logic**

- **Emotion Usage Tracking:** The assistant tracks how often each emotion/mood/animation is used, and biases future selections to encourage variety.
- **Flexible Time Parsing:** Reminders can be set using various time formats, with logic to parse and schedule them correctly.
- **Dynamic Tool Context:** When asking the LLM to select an animation, the script injects real-time usage data to influence its choice.
- **Workflow Orchestration:** The assistant can execute complex, multi-step workflows as suggested by the LLM, integrating multiple services and APIs.

---

## **Summary Table**

| Component         | Purpose/Responsibility                                                                 | Notable Features/Logic                          |
|-------------------|---------------------------------------------------------------------------------------|-------------------------------------------------|
| TextToSpeech      | ElevenLabs TTS wrapper and audio playback                                             | Temp file handling, config-driven               |
| GPTClient         | OpenAI GPT chat wrapper, animation/mood selection, workflow suggestion                | Emotion tracking, dynamic tool context          |
| Functions         | Tool dispatcher: executes LLM-suggested actions (weather, reminders, agents, etc.)    | Async event scheduling, TTS narration           |
| Helper Functions  | Config loading, utility imports, weather code mapping, tool list building             | Config-driven, modular imports                  |
| External Services | OpenAI, ElevenLabs, Google, Spotify, Open-Meteo, API Ninjas                           | API integration, error handling                 |

---

## **Conclusion**

This script is a sophisticated integration layer for a conversational assistant, enabling it to interact with LLMs, synthesize speech, orchestrate workflows across multiple APIs, and provide a rich, interactive user experience. Its design emphasizes modularity, extensibility, and a high degree of configurability, making it suitable as the core logic for an advanced AI assistant.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\llm_client_utils.py
Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script provides **shared utility functions and tool definitions** for an LLM (Large Language Model) client, likely as part of a chatbot or virtual assistant system. It centralizes configuration loading, API integrations (joke, quote, city coordinates), weather code descriptions, and the definition of callable "tools" (functions) that the LLM can invoke to perform various tasks on behalf of the user.

---

## **Main Components**

### 1. **Weather Code Descriptions**

- **Purpose:**  
  A dictionary mapping weather condition codes (integers) to human-readable descriptions.  
- **Usage:**  
  Intended for interpreting or displaying weather data from APIs that use numeric codes.

---

### 2. **Configuration Loader**

- **Function:** `_load_config()`
- **Purpose:**  
  Loads a shared YAML configuration file (`config.yaml`) from a relative path.
- **Responsibilities:**  
  - Locates the config file based on the script's directory.
  - Loads and parses the YAML file using `yaml.safe_load`.
  - Provides access to secrets (API keys) and other configuration data.
- **Dependencies:**  
  - `os` for path handling.
  - `yaml` for YAML parsing.
- **Configuration Requirement:**  
  Requires a `config.yaml` file in a `config` directory one level above the script.

---

### 3. **API Utility Functions**

These functions encapsulate external API calls and return formatted results for the LLM to use.

#### a. **get_joke()**
- **Purpose:**  
  Fetches a random joke from the [Official Joke API](https://official-joke-api.appspot.com/).
- **Logic:**  
  - Sends a GET request.
  - Extracts and formats the joke's setup and punchline.
- **Dependencies:**  
  - `requests` for HTTP requests.

#### b. **get_quote()**
- **Purpose:**  
  Retrieves a motivational quote from the [API Ninjas Quotes API](https://api-ninjas.com/api/quotes).
- **Logic:**  
  - Loads API key from config.
  - Sends a GET request with the required header.
  - Extracts the first quote and author from the JSON response.
- **Dependencies:**  
  - `requests`
  - API key in config under `secrets.api_ninjas_api_key`.

#### c. **get_city_coordinates(city)**
- **Purpose:**  
  Gets latitude and longitude for a given city using the [API Ninjas City API](https://api-ninjas.com/api/city).
- **Logic:**  
  - Loads API key from config.
  - Sends a GET request with the city name.
  - Extracts coordinates from the response.
- **Dependencies:**  
  - `requests`
  - API key in config.

---

### 4. **Tool Definitions**

These are **structured definitions** (as dictionaries) of functions/tools that the LLM can call. They are likely used for function-calling capabilities in LLM frameworks (e.g., OpenAI's function calling, LangChain tools).

#### a. **set_animation_tool**
- **Purpose:**  
  Describes a function for setting the bot's animation/mood based on context.
- **Structure:**  
  - Specifies allowed animation states (e.g., happy, angry, sad, etc.).
  - Describes the function's intent and parameters.

#### b. **build_tools()**
- **Purpose:**  
  Returns a list of tool/function definitions that the LLM can invoke.
- **Logic:**  
  - Loads configuration for web search tool (e.g., user location, context size).
  - Dynamically includes current date and time in weather tool description.
  - Defines a variety of tools, each as a dictionary specifying:
    - Type (always "function" except for web search).
    - Name.
    - Description (often with usage guidance for the LLM).
    - Parameters (with types, requirements, and validation).
  - Returns the complete list of tools.
- **Notable Tools Defined:**
  - **Web Search Tool:** For searching the web, with optional user location/context.
  - **get_weather:** For weather queries, with flexible parameters (forecast days, units, etc.).
  - **test_function:** For testing function-calling.
  - **get_joke, get_quote, get_city_coordinates:** For jokes, quotes, and city info.
  - **get_advice:** For advice (implementation not shown).
  - **call_google_agent:** Delegates Google-related requests (calendar, etc.) to a Google Agent.
  - **call_spotify_agent:** Delegates Spotify/music requests to a Spotify Agent, with device ID validation.
  - **set_timer, set_reminder:** For timers and reminders, with detailed parameter validation.
  - **daily_summary:** For generating a daily summary from various sources.

---

## **Structure and Interactions**

- **Configuration** is loaded once per function call (could be optimized by caching).
- **API utility functions** use configuration to access secrets and interact with external APIs.
- **Tool definitions** are static (except for weather tool, which includes dynamic date/time info).
- **build_tools()** is the main entry point for retrieving all available tools for the LLM.
- **External dependencies:**  
  - `requests` (HTTP requests)
  - `yaml` (YAML parsing)
  - `os` (filesystem paths)
  - `datetime` (current time)
- **APIs used:**  
  - Official Joke API
  - API Ninjas (Quotes and City endpoints)
- **Configuration:**  
  - Requires a YAML file with secrets (API keys) and web search settings.

---

## **Notable Logic and Algorithms**

- **Dynamic Tool Descriptions:**  
  The weather tool's description dynamically includes the current day and time, and contains logic notes for the LLM about how to interpret user requests for "weekend" forecasts.
- **Parameter Validation:**  
  Each tool/function definition specifies parameter types, required fields, and constraints (e.g., allowed values, regex patterns for device IDs).
- **Delegation Pattern:**  
  Some tools (e.g., Google/Spotify agents) are designed to delegate user requests to specialized sub-agents, supporting modularity and extensibility.
- **API Key Management:**  
  API keys are not hardcoded but loaded from a configuration file, improving security and flexibility.

---

## **Summary Table**

| Component                | Purpose                                           | External Dependency | Config Required? | Notable Logic/Features                |
|--------------------------|---------------------------------------------------|---------------------|------------------|----------------------------------------|
| WEATHER_CODE_DESCRIPTIONS| Weather code to description mapping               | None                | No               | Static mapping                         |
| _load_config             | Load YAML config (API keys, settings)             | yaml, os            | Yes              | Loads from relative path               |
| get_joke                 | Fetch random joke                                 | requests            | No               | Formats joke for LLM                   |
| get_quote                | Fetch motivational quote                          | requests            | Yes              | Uses API key from config               |
| get_city_coordinates     | Fetch city coordinates                            | requests            | Yes              | Uses API key from config               |
| set_animation_tool       | Define animation/mood setting tool                | None                | No               | Enum of allowed moods                  |
| build_tools              | Define all callable LLM tools                     | datetime, os, yaml  | Yes              | Dynamic tool list, parameter schemas   |

---

## **Conclusion**

This script is a **utility and tool definition module** for an LLM-based assistant, providing configuration management, API integrations, and a structured interface for function-calling. It is designed for extensibility, modularity, and safe configuration handling, and is intended to be imported and used by higher-level components of the LLM client system. The code is heavily reliant on external configuration and APIs, and is structured to support a wide range of assistant actions through well-defined tool schemas.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\spotify_agent.py
Here is a detailed summary and analysis of the provided `spotify_agent.py` script:

---

## **Overall Purpose**

The script implements a **Spotify Agent** that can interpret natural language user requests and map them to Spotify actions using a set of defined tools (functions). It leverages a Large Language Model (LLM, via OpenAI API) to decide which Spotify tool to use for a given user request, and then executes the corresponding action via a Spotify Home Assistant utility (`SpotifyHA`). The agent supports a range of Spotify operations, such as searching for tracks, managing playback, queueing songs, listing devices, and more.

---

## **Main Components**

### 1. **External Dependencies**

- **openai**: For LLM-based decision-making.
- **yaml**: For loading configuration files.
- **spotify_ha_utils.SpotifyHA**: Custom utility for interacting with Spotify (authentication, playback, queue, etc.).
- **json, os, datetime, typing**: Standard Python libraries for data handling, configuration, and type hints.

### 2. **SPOTIFY_TOOLS**

- A list of dictionaries, each describing a "tool" (function) that the agent can perform.
- Each tool includes:
  - `name`: The function name.
  - `description`: What the function does.
  - `parameters`: Expected arguments (with types, defaults, and requirements).
- Tools cover a wide range of Spotify actions, including:
  - Playback control (play/pause, skip, transfer playback).
  - Track/album search and queueing.
  - Device management.
  - Retrieving current, queued, or recently played tracks.

### 3. **SpotifyAgent Class**

#### **Responsibilities:**

- **Configuration and Initialization**
  - Loads configuration (YAML) for secrets (e.g., OpenAI API key) and LLM model.
  - Initializes the SpotifyHA interface for Spotify API access.

- **Dispatching Actions**
  - `_dispatch`: Maps a tool name and arguments to the corresponding SpotifyHA method, handling argument parsing and formatting of results.
  - Each tool in `SPOTIFY_TOOLS` has a corresponding handler in `_dispatch`.

- **LLM Integration**
  - `llm_decide_and_dispatch`: Constructs a prompt for the LLM, including the list of available tools and the user request.
  - Calls the LLM (via OpenAI API) to select the most appropriate tool and arguments.
  - Executes the selected tool by calling `_dispatch`.

#### **Structure:**

- **Static Method:**
  - `_load_config`: Loads configuration from a YAML file.

- **Constructor (`__init__`):**
  - Loads config, initializes SpotifyHA, sets up OpenAI API key and LLM model, and stores the tool definitions.

- **Dispatch Method (`_dispatch`):**
  - Receives a tool name and arguments, parses arguments, and routes the call to the appropriate SpotifyHA method.
  - Handles formatting of results for user-friendly output.

- **LLM Interface (`llm_decide_and_dispatch`):**
  - Prepares a system prompt listing all tools.
  - Passes user request and arguments to the LLM.
  - Expects the LLM to return a function call, which is then dispatched.

### 4. **Helper Function: _pretty**

- Formats and prints the output of SpotifyAgent actions for command-line use.
- Handles various data structures (dicts, lists) to display track info, statuses, and device lists in a readable way.

### 5. **Command-Line Interface**

- If run as a script, starts an interactive loop:
  - Prompts the user for input.
  - Passes input to the agent.
  - Prints formatted results.
  - Handles exit on Ctrl-C or EOF.

---

## **Component Interactions**

1. **User Input** (via CLI or other interface).
2. **SpotifyAgent.llm_decide_and_dispatch**:
   - Builds a prompt with the user request and tool descriptions.
   - Calls the LLM to select the best tool and arguments.
   - Receives the LLM's function call output.
3. **SpotifyAgent._dispatch**:
   - Maps the function call to the correct SpotifyHA method.
   - Executes the action and formats the result.
4. **Output**:
   - The result is formatted (via `_pretty`) and displayed to the user.

---

## **External Dependencies & Configuration**

- **SpotifyHA**: Custom utility for Spotify API access. Requires valid Spotify authentication.
- **OpenAI API**: Requires an API key, provided in the YAML config.
- **YAML Config File**: Located at `config/config.yaml` (relative to the script's parent directory). Must contain:
  - `secrets.openai_api_key`
  - `llm.model`
- **openai-python** and **pyyaml** libraries must be installed.

---

## **Notable Algorithms and Logic**

- **LLM Tool Selection**: The agent uses an LLM to interpret natural language and select the most appropriate tool, ensuring only one tool is chosen per request. This abstracts complex intent parsing and mapping to function calls.
- **Dynamic Dispatch**: The `_dispatch` method dynamically routes requests to the correct SpotifyHA method based on the tool name, handling argument parsing and result formatting.
- **Queue and Device Formatting**: For queue and device listing, the agent builds human-readable summaries, including ETA for queued tracks and detailed device info.

---

## **Summary Table**

| Component       | Responsibility                                               |
|-----------------|-------------------------------------------------------------|
| SPOTIFY_TOOLS   | Defines all available Spotify actions/tools                  |
| SpotifyAgent    | Handles config, LLM interaction, and dispatching actions     |
| _pretty         | Formats and prints results for the user                     |
| CLI Loop        | Provides an interactive command-line interface               |
| SpotifyHA       | (External) Handles actual Spotify API calls                  |
| openai          | (External) Provides LLM-based tool selection                 |
| yaml            | Loads configuration                                         |

---

## **Key Points**

- **Purpose**: Natural language Spotify control via LLM-driven tool selection and execution.
- **Main Class**: `SpotifyAgent` – handles configuration, LLM interaction, and dispatching.
- **Tools**: Defined in `SPOTIFY_TOOLS`, mapped to SpotifyHA methods.
- **LLM Use**: Converts user requests into structured function calls.
- **Config**: Requires YAML config with OpenAI API key and model.
- **Extensibility**: New tools can be added to `SPOTIFY_TOOLS` and handled in `_dispatch`.

---

**In summary:**  
This script is a modular, LLM-driven agent for controlling Spotify through natural language, using a set of well-defined tools and a dispatch mechanism to map LLM-selected actions to actual Spotify API calls, with a focus on user-friendly interaction and extensibility.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\spotify_ha_utils.py
Here is a detailed summary and analysis of the provided Python script `spotify_ha_utils.py` (v5.3):

---

## **Overall Purpose**

This script provides a high-level, object-oriented utility wrapper around the [Spotipy](https://spotipy.readthedocs.io/) library for interacting with the Spotify Web API, with a focus on queue and playback management. It is designed to be used in Home Assistant (hence the `ha` in the name) or other automation/CLI contexts. The script also includes a pretty command-line interface (CLI) demo (optionally using [Rich](https://rich.readthedocs.io/)) and supports advanced queue manipulation, artist/album helpers, and playlist/history utilities.

---

## **Main Components**

### **1. Configuration Loader**

- **Function:** `_load_cfg`
- **Purpose:** Loads a YAML configuration file (default: `config/config.yaml`) containing Spotify API credentials (`client_id`, `client_secret`).
- **Interaction:** Used during `SpotifyHA` initialization for authentication.

### **2. SpotifyHA Class**

The core of the script is the `SpotifyHA` class, which encapsulates all Spotify API interactions.

#### **Construction & Authentication**

- **Constructor:** Accepts scopes, config path, redirect URI, and browser options.
- **Authentication:** Uses Spotipy’s `SpotifyOAuth` for user authentication, reading credentials from the loaded YAML config.
- **Singleton:** Provides a `get_default()` class method to instantiate or retrieve a singleton instance.

#### **Helpers**

- **_flat:** Flattens a Spotify track object into a simplified dictionary for easier handling and display.
- **_ms_to_mmss:** Converts milliseconds to a human-readable time string.
- **_fmt_track:** Formats a track for display.

#### **Playback State & Queue**

- **get_current_playback / get_current_track / is_playing:** Retrieve current playback state and track.
- **get_queue:** Gets the current playback queue.
- **_queue_wait_times:** Calculates the ETA (in ms) for each track in the queue, based on the current playback position.

#### **Device Helpers**

- **list_devices / get_active_device:** List available playback devices and get the currently active one.
- **_with_device:** Ensures a valid device ID is used for playback actions.

#### **Playback Control**

- **play / pause / skip_next / skip_previous / toggle_play_pause / transfer_playback / start_playback:** Standard playback controls, all device-aware.

#### **Search & Queue Helpers**

- **search_tracks:** Search for tracks by free-text query.
- **add_to_queue:** Add a track to the queue, with optional verification.
- **play_track:** Immediately play a specific track.
- **search_and_queue_track:** Search for a track and queue it (optionally picking the first or a random result).

#### **Queue Removal**

- **remove_from_queue:** Precisely removes a track at a given position in the queue by skipping forward, removing, and re-queuing skipped tracks.

#### **Artist Helpers**

- **_best_artist:** Picks the best matching artist from a list, prioritizing exact name match or most followers.
- **artist_top_track:** Finds the top track for a given artist (by name), optionally queues it, and returns its details.

#### **Playlists & History**

- **save_current_track_to_playlist:** Adds the currently playing track to a specified playlist.
- **get_recently_played:** Returns the user's recently played tracks.

#### **Album Playback**

- **play_album_by_name:** Searches for an album (optionally by artist) and starts playback of that album.

#### **CLI Demo**

- **demo:** Demonstrates queuing a track and displays the queue with ETA, using Rich tables if available, or plain text otherwise.

---

## **External Dependencies**

- **spotipy:** For all Spotify Web API interactions.
- **yaml:** For configuration file parsing.
- **rich (optional):** For pretty CLI output (tables, colors).
- **Standard Library:** `random`, `time`, `pathlib`, `typing`.

---

## **Configuration Requirements**

- **YAML Config:** Must provide a `config.yaml` file with a `secrets` section containing `spotify_client_id` and `spotify_client_secret`.
- **Spotify Developer Account:** Required to obtain API credentials.
- **Scopes:** The script requests both read and write scopes for playback and playlist management.

---

## **Notable Algorithms & Logic**

### **1. Precise Queue Removal**

Spotify's API does not support removing arbitrary tracks from the queue. The script works around this by:
- Skipping forward to the desired track.
- Skipping it (effectively removing it from the queue).
- Re-queuing any tracks that were ahead of it, in reverse order, to restore the original queue order.

### **2. Artist Selection**

When searching for an artist, the script:
- Attempts to find an exact name match (case-insensitive).
- If not found, selects the artist with the most followers (assuming this is the most popular/likely desired artist).

### **3. Queue ETA Calculation**

- For each track in the queue, the script calculates the time until it will play, based on the current track’s remaining time and the durations of queued tracks.

### **4. CLI Demo with Rich**

- If Rich is installed, the demo displays the queue in a styled table with ETAs.
- If not, falls back to plain text output.

---

## **Structure & Component Interaction**

- **Initialization:** User creates a `SpotifyHA` instance (or uses the singleton).
- **Authentication:** Loads credentials from config and authenticates via Spotipy.
- **Playback/Queue Operations:** User calls methods on `SpotifyHA` to control playback, manipulate the queue, or query state.
- **Helpers:** Internal helpers format and process Spotify API responses for easier use and display.
- **CLI Demo:** Can be run as a script to demonstrate functionality.

---

## **Summary Table**

| Component         | Purpose                                           | Key Methods/Functions                       |
|-------------------|--------------------------------------------------|---------------------------------------------|
| Config Loader     | Load YAML config with Spotify credentials         | `_load_cfg`                                 |
| SpotifyHA         | Main OO Spotify API wrapper                       | All playback, queue, search, playlist, etc. |
| CLI Demo          | Pretty-print queue and ETA (Rich optional)        | `demo`                                      |
| External Deps     | Spotify API, YAML, Rich (optional)                | spotipy, yaml, rich                         |
| Notable Logic     | Precise queue removal, artist selection, ETA calc | `remove_from_queue`, `_best_artist`, `_queue_wait_times` |

---

## **Conclusion**

This script is a robust, user-friendly, and extensible utility for Spotify playback and queue management, suitable for automation, scripting, or CLI use. It abstracts away Spotipy’s lower-level details, adds advanced queue/artist logic, and provides a pleasant CLI experience with minimal setup (just a YAML config and Spotipy credentials). The code is modular, with clear separation between configuration, API interaction, helpers, and user-facing features.
