# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\google_agent.py
### Overview

The script is designed to interact with Google Calendar using the Google Calendar API and OpenAI's API. It provides functionalities to list calendars, fetch upcoming events, and potentially create or delete events based on user requests. The script consists of two main classes: `GoogleCalendarManager` and `GoogleAgent`.

### Main Classes and Functions

#### GoogleCalendarManager

- **Purpose**: Manages interactions with Google Calendar, including authentication and event retrieval.
  
- **Key Methods**:
  - `_load_config`: Loads configuration data from a YAML file, including API credentials and settings.
  - `__init__`: Initializes the Google Calendar API client using credentials and loads configuration settings.
  - `get_google_credentials`: Handles authentication, either by loading existing credentials or initiating a new OAuth flow if necessary.
  - `list_calendars`: Retrieves a list of calendars, excluding those specified in the configuration to be skipped.
  - `get_upcoming_events`: Fetches upcoming events from the user's calendars for a specified number of days.
  - `print_calendars`: Prints the list of available calendars.
  - `print_upcoming_events`: Prints upcoming events for the specified duration.

#### GoogleAgent

- **Purpose**: Acts as an intermediary between user requests and Google Calendar operations, utilizing OpenAI's API to decide which actions to take.
  
- **Key Methods**:
  - `_load_config`: Similar to `GoogleCalendarManager`, loads configuration data from a YAML file.
  - `__init__`: Initializes the agent with OpenAI API key, calendar manager, and tool definitions.
  - `llm_decide_and_dispatch`: Uses OpenAI's language model to determine which calendar operation to perform based on user input.
  - `dispatch`: Executes the chosen calendar operation by calling the appropriate method in `GoogleCalendarManager`.
  - `get_google_calendar_events`: Retrieves upcoming events using the calendar manager.
  - `print_calendars` and `print_upcoming_events`: Wrapper methods that call the corresponding methods in `GoogleCalendarManager`.

### Structure and Interaction

The script is structured around two main classes that handle different aspects of the functionality. `GoogleCalendarManager` deals with direct interactions with Google Calendar, while `GoogleAgent` uses OpenAI's API to interpret user requests and decide on actions. The agent uses a predefined set of tools (functions) that it can choose from based on the user's input.

### External Dependencies and Configuration

- **APIs**: 
  - Google Calendar API: Used for calendar and event management.
  - OpenAI API: Used for natural language processing to interpret user requests.

- **Dependencies**:
  - `google-auth`, `google-auth-oauthlib`, `google-api-python-client`: Required for Google Calendar API authentication and interaction.
  - `openai`: Required for interacting with OpenAI's API.
  - `yaml`: Used for configuration file parsing.
  - `json`, `os`, `datetime`: Standard libraries for JSON handling, file operations, and date-time manipulation.

- **Configuration**: The script relies on a YAML configuration file (`config.yaml`) to store API keys, client secrets, and other settings. This file must be correctly set up for the script to function.

### Notable Algorithms and Logic

- **OAuth Authentication**: The script includes logic to handle Google OAuth authentication, including token refreshing and saving credentials to a file.
- **Tool Selection**: The `llm_decide_and_dispatch` method uses OpenAI's language model to select the appropriate tool (function) based on user input. This involves constructing a prompt with available tools and interpreting the model's response to choose an action.
- **Event Filtering**: The script filters out calendars specified in the configuration to be skipped, ensuring only relevant calendars are processed.

Overall, the script provides a framework for integrating Google Calendar functionalities with AI-driven decision-making to automate calendar management tasks.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\llm_client.py
The script is a complex Python application designed to interact with various APIs and services, primarily focusing on text-to-speech (TTS), natural language processing (NLP) using OpenAI's GPT, and managing workflows with external services like Google Calendar and Spotify.

### Overall Purpose
The script aims to create an intelligent assistant capable of generating and playing audio from text, interacting with OpenAI's GPT for conversation and task execution, and managing workflows involving external services like Google Calendar and Spotify. It also includes functionalities for weather retrieval, jokes, quotes, and advice.

### Main Components

#### 1. **Configuration Loading**
- `_load_config`: Loads configuration settings from a YAML file, which includes API keys and other settings necessary for the script's operation.

#### 2. **Text-to-Speech (TTS)**
- **Class `TextToSpeech`**: Manages the conversion of text to speech using the ElevenLabs API.
  - **Attributes**: API key, voice settings, model ID, and output format.
  - **Methods**:
    - `elevenlabs_generate_audio`: Generates audio from text.
    - `generate_and_play_advanced`: Plays the generated audio and handles temporary file management.

#### 3. **OpenAI GPT Client**
- **Class `GPTClient`**: Interfaces with the OpenAI API to generate text responses based on input conversations.
  - **Attributes**: API key, model, TTS settings, emotion counter.
  - **Methods**:
    - `get_text`: Retrieves text responses from OpenAI.
    - `reply_with_animation`: Generates animated replies based on emotion counters.
    - `get_workflow`: Retrieves a workflow of tasks to execute based on input.

#### 4. **Function Execution**
- **Class `Functions`**: Executes various tasks and functions based on workflows generated by the `GPTClient`.
  - **Attributes**: Instances of `GPTClient`, `GoogleAgent`, `SpotifyAgent`, and configuration settings.
  - **Methods**:
    - `execute_workflow`: Executes a series of tasks based on the provided workflow.
    - `get_weather`: Retrieves weather information using an external API.
    - `_schedule_timer_event`: Schedules a timer event.
    - `get_advice`: Retrieves advice from an external API.
    - `set_reminder`: Schedules a reminder event.

### External Dependencies and APIs
- **OpenAI API**: For generating text responses.
- **ElevenLabs API**: For text-to-speech conversion.
- **Google Calendar API**: Managed by `GoogleCalendarManager` for calendar events.
- **Spotify API**: Managed by `SpotifyAgent` for music-related tasks.
- **Open-Meteo API**: For weather information.
- **API Ninjas**: For advice retrieval.

### Configuration Requirements
- A YAML configuration file (`config.yaml`) containing API keys and settings.
- JSON file for emotion counters (`emotion_counter.json`).

### Notable Logic
- **Emotion Counter**: Tracks the usage of emotions in responses to provide varied and less repetitive interactions.
- **Workflow Execution**: Dynamically executes tasks based on the generated workflow, integrating with multiple services.
- **Audio Playback**: Efficiently manages audio file creation and playback using temporary files.

### Structure and Interaction
- The script initializes various agents and clients to handle specific tasks.
- Configuration settings are loaded at the start to provide necessary parameters for API interactions.
- The `Functions` class acts as the central hub, executing workflows and interacting with other components like TTS and GPT.
- The main function demonstrates usage with Google Calendar, printing calendars and events.

This script is a sophisticated integration of multiple services, providing a foundation for building an intelligent assistant with capabilities in speech, conversation, and task management.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\llm_client_utils.py
The provided Python script, `llm_client_utils.py`, is designed to offer utility functions and tool definitions that can be integrated into a larger application, likely involving a conversational AI or a chatbot. The script includes functions for fetching jokes, quotes, city coordinates, and building a set of tools for various functionalities.

### Overall Purpose
The script's main purpose is to provide utility functions that can be used to enhance the capabilities of a chatbot or virtual assistant. It includes functions for fetching jokes, quotes, and city coordinates, as well as defining a set of tools that can be used to perform various tasks such as setting timers, reminders, and interacting with external services like Google and Spotify.

### Main Components

1. **Weather Code Descriptions:**
   - A dictionary mapping weather codes to their respective descriptions. This is likely used for interpreting weather data.

2. **Configuration Loading:**
   - `_load_config()`: This function loads configuration data from a YAML file located in a `config` directory. The configuration includes API keys and other settings necessary for the script's operations.

3. **Utility Functions:**
   - `get_joke()`: Fetches a random joke from an external API (`official-joke-api.appspot.com`) and formats it for user presentation.
   - `get_quote()`: Retrieves a random inspirational quote using the API Ninjas service, requiring an API key from the configuration.
   - `get_city_coordinates(city)`: Obtains latitude and longitude for a specified city using the API Ninjas service, also requiring an API key.

4. **Tool Definitions:**
   - `set_animation_tool`: A predefined tool for setting animations based on emotional states, useful for a chatbot's visual representation.
   - `build_tools()`: Constructs a list of tool definitions that include functionalities like weather retrieval, joke and quote fetching, city coordinate lookup, and interactions with Google and Spotify services. Each tool is defined with a type, name, description, and parameters.

### External Dependencies and APIs
- **Requests Library:** Used for making HTTP requests to external APIs.
- **PyYAML Library:** Used for parsing YAML configuration files.
- **External APIs:**
  - Official Joke API for jokes.
  - API Ninjas for quotes and city data.
  
### Configuration Requirements
- The script requires a `config.yaml` file containing API keys and other settings. The file is expected to be located in a `config` directory relative to the script's location.

### Notable Algorithms and Logic
- **Tool Construction:** The `build_tools()` function dynamically constructs a list of tools with specific functionalities. It uses the current date and time to provide context for weather-related tools and configures web search tools based on user location and context size from the configuration.
- **API Interaction:** The script demonstrates interaction with external APIs, handling responses, and extracting relevant data to be used within the application.

### Interaction of Components
- The utility functions rely on the configuration loaded by `_load_config()` to access necessary API keys.
- The tools defined in `build_tools()` are likely used by a larger application to perform specific tasks, such as fetching weather data or interacting with external services like Google and Spotify.

Overall, the script is structured to provide modular and reusable components that can be integrated into a conversational AI system, enhancing its ability to interact with users and external services.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\spotify_agent.py
### Overview

The script `spotify_agent.py` is designed to interact with Spotify's API, providing a command-line interface for managing music playback and querying information. It leverages a language model (LLM) to interpret user requests and map them to specific Spotify actions. The script includes a variety of tools to search, play, and manage music tracks and devices.

### Main Components

#### Classes and Functions

1. **SpotifyAgent Class**: 
   - **Purpose**: Acts as the main interface for interacting with Spotify. It loads configuration, initializes Spotify and OpenAI API connections, and dispatches user requests to appropriate Spotify functions.
   - **Key Methods**:
     - `_load_config`: Loads configuration from a YAML file, containing API keys and model settings.
     - `__init__`: Initializes the agent, loading configuration and setting up Spotify and OpenAI connections.
     - `_dispatch`: Maps function names to their corresponding Spotify actions, executing them with provided arguments.
     - `llm_decide_and_dispatch`: Uses the LLM to decide which Spotify tool to use based on user input and dispatches the request.

2. **_pretty Function**: 
   - **Purpose**: Formats and prints the output from Spotify actions in a user-friendly way.

### Tools and Their Responsibilities

The script defines a set of tools, each corresponding to a specific Spotify action. These tools are represented as dictionaries with metadata such as name, description, and parameters. Key tools include:

- **get_current_track**: Retrieves information about the currently playing track.
- **get_queue**: Returns the upcoming queue of tracks with estimated time of arrival (ETA).
- **toggle_play_pause**: Toggles between playing and pausing the current track.
- **skip_next_track**: Skips to the next track in the queue.
- **search_tracks**: Searches for tracks based on a text query.
- **queue_track_by_name**: Finds and queues a track by name.
- **list_devices**: Lists all available Spotify playback devices.
- **transfer_playback**: Transfers playback to a specified device.
- **get_recently_played**: Retrieves the user's recently played tracks.
- **play_album_by_name**: Searches and plays an album by name.

### External Dependencies

- **SpotifyHA**: A utility module for interacting with Spotify's API. The script attempts to import this module from two potential locations.
- **OpenAI**: Used for language model processing to interpret user requests and decide on actions.
- **YAML**: For configuration management, loading API keys and model settings.

### Configuration

The script requires a configuration file (`config.yaml`) located in a `config` directory. This file must contain API keys for OpenAI and settings for the language model.

### Notable Logic

- **Dispatch Mechanism**: The `_dispatch` method uses a mapping of function names to execute the corresponding Spotify actions. It handles argument parsing and ensures the correct function is called with the appropriate parameters.
- **LLM Integration**: The `llm_decide_and_dispatch` method constructs a prompt for the language model, which includes a list of available tools and the current date and time. The LLM's response determines which tool to invoke.

### User Interaction

The script runs a command-line interface that continuously prompts the user for input. It processes each input through the `llm_decide_and_dispatch` method, executing the corresponding Spotify action and displaying the result using the `_pretty` function.

Overall, `spotify_agent.py` provides a robust interface for managing Spotify playback through natural language commands, leveraging both Spotify's API and OpenAI's language model capabilities.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\spotify_ha_utils.py
### Overview

The script `spotify_ha_utils.py` is a utility for interacting with Spotify's API, primarily focused on managing playback and queue operations. It provides a command-line interface (CLI) demonstration using the Rich library, which is optional. The script includes features like searching and queuing tracks, auto-selecting artists, and precisely removing tracks from the queue.

### Main Components

#### External Dependencies

- **Spotipy**: A lightweight Python library for the Spotify Web API, used for authentication and API interactions.
- **PyYAML**: For loading configuration files.
- **Rich**: An optional library for creating a visually appealing CLI with tables and formatted text.

#### Configuration

- The script loads configuration details, such as Spotify API credentials, from a YAML file (`config.yaml`).

### Key Classes and Functions

#### `SpotifyHA` Class

This class is a wrapper around Spotipy, providing methods for interacting with Spotify playback and queue.

- **Initialization**: Authenticates with Spotify using credentials from a configuration file. It sets up the Spotipy client with the necessary scopes for reading and modifying playback.

- **Helper Methods**:
  - `_flat`: Simplifies track information into a dictionary with key details.
  - `_ms_to_mmss`: Converts milliseconds to a `mm:ss` format.
  - `_fmt_track`: Formats track information for display.

- **Playback Methods**:
  - `get_current_playback`, `get_current_track`, `is_playing`: Retrieve current playback status and track information.
  - `list_devices`, `get_active_device`, `_with_device`: Manage Spotify devices for playback.
  - `play`, `pause`, `skip_next`, `skip_previous`, `toggle_play_pause`, `transfer_playback`, `start_playback`: Control playback operations.

- **Queue Management**:
  - `get_queue`, `_queue_wait_times`: Retrieve and calculate wait times for tracks in the queue.
  - `add_to_queue`, `remove_from_queue`: Add or remove tracks from the queue with verification and precise positioning.

- **Search and Queue**:
  - `search_tracks`, `search_and_queue_track`: Search for tracks and queue them based on a query.
  - `artist_top_track`: Automatically select and queue top tracks from an artist.

- **Playlist and History**:
  - `save_current_track_to_playlist`: Save the currently playing track to a specified playlist.
  - `get_recently_played`: Retrieve recently played tracks.

- **Album Playback**:
  - `play_album_by_name`: Search for an album and start its playback.

- **CLI Demo**:
  - `demo`: Demonstrates the usage of the class with a CLI interface, optionally using Rich for enhanced display.

### Notable Logic

- **Queue Management**: The script includes logic to verify that a track is successfully added to the queue and allows precise removal of tracks by skipping and re-queuing tracks ahead of the target.

- **Artist Selection**: The `_best_artist` method selects the best artist match based on the query or the number of followers.

### Interaction and Execution

- The script can be executed directly, which will run the `demo` method using the default `SpotifyHA` instance. This demonstrates the functionality by queuing a random track from the specified artist and displaying the queue with estimated wait times.

### Configuration Requirements

- A `config.yaml` file must be present with Spotify API credentials (`spotify_client_id` and `spotify_client_secret`) under a `secrets` key.

### Conclusion

This script provides a comprehensive set of tools for managing Spotify playback and queues, with additional features for artist and album handling. It is designed for both programmatic use and interactive CLI demonstrations, leveraging Spotipy and optionally Rich for enhanced user interaction.
