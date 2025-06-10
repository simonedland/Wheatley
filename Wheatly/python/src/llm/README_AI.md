# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\google_agent.py
The Python script is designed to integrate with Google Calendar and provide an interface for interacting with calendar events using a language model (LLM) agent. It consists of two main classes: `GoogleCalendarManager` and `GoogleAgent`.

### Purpose

The script aims to facilitate interaction with Google Calendar by:
1. Fetching and displaying calendar events.
2. Providing a framework for creating and deleting events (though these are not fully implemented).
3. Using a language model to decide which calendar-related action to perform based on user input.

### Main Classes and Functions

#### GoogleCalendarManager

- **Purpose**: Acts as a wrapper for Google Calendar API interactions.
- **Responsibilities**:
  - **Authentication**: Manages Google API credentials, refreshing tokens, and handling authentication errors.
  - **Configuration Loading**: Loads configuration from a YAML file, including credentials and calendar settings.
  - **Calendar Management**:
    - `list_calendars`: Retrieves a list of calendars, excluding those specified in the configuration to skip.
    - `get_upcoming_events`: Fetches upcoming events from the calendars for a specified number of days.
    - `print_calendars`: Prints the list of available calendars.
    - `print_upcoming_events`: Prints upcoming events in a user-friendly format.

#### GoogleAgent

- **Purpose**: Acts as an LLM-driven assistant for interacting with Google services.
- **Responsibilities**:
  - **Configuration Loading**: Loads API keys and model configurations from a YAML file.
  - **Tool Management**: Maintains a list of available Google tools (functions) for interacting with the calendar.
  - **Decision Making**:
    - `llm_decide_and_dispatch`: Uses the LLM to decide which tool to use based on user input and dispatches the appropriate function.
  - **Function Dispatch**:
    - `dispatch`: Executes the chosen function with the provided arguments.
    - `get_google_calendar_events`: Fetches upcoming events using the `GoogleCalendarManager`.
    - Placeholder functions for creating and deleting events, which are not implemented.

### Structure and Interaction

1. **Configuration**: Both classes load configuration details from a YAML file located in a `config` directory. This includes API keys and calendar settings.
2. **Authentication**: The `GoogleCalendarManager` handles authentication with Google Calendar, using OAuth2 credentials stored in a JSON file.
3. **LLM Integration**: The `GoogleAgent` uses OpenAI's API to process user requests and determine which calendar function to execute.
4. **Tool Execution**: Based on the LLM's decision, the agent executes the appropriate function to interact with Google Calendar.

### External Dependencies

- **Google APIs**: Uses `google-auth`, `google-auth-oauthlib`, and `google-api-python-client` for authentication and API requests.
- **OpenAI API**: Utilizes OpenAI's API for language model processing.
- **YAML**: Uses `pyyaml` for configuration management.

### Notable Algorithms and Logic

- **LLM Decision Making**: The `llm_decide_and_dispatch` function constructs a prompt for the LLM, describing available tools and asking it to choose the best one based on the user's request. The LLM's response is parsed to determine which function to call.
- **Event Fetching**: The `get_upcoming_events` method efficiently retrieves events within a specified time range and organizes them by calendar.

### Configuration Requirements

- A `config.yaml` file must be present with the necessary API keys and settings.
- OAuth2 credentials need to be set up and stored in a `token.json` file for Google Calendar access.

Overall, the script provides a structured approach to managing Google Calendar events with the potential for expansion to include event creation and deletion, leveraging the capabilities of an LLM for decision-making.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\llm_client.py
The provided Python script is a comprehensive implementation for an assistant that interacts with various APIs to perform tasks such as text-to-speech, chat interactions, and workflow execution. Here's a detailed breakdown of its components and functionalities:

### Overall Purpose
The script serves as a client wrapper for various APIs, enabling an assistant to perform tasks like generating speech from text, interacting with OpenAI's GPT models, managing workflows, and integrating with external services like Google Calendar and Spotify.

### Main Components

1. **External Dependencies**:
   - **OpenAI**: Used for GPT model interactions.
   - **ElevenLabs**: Provides text-to-speech capabilities.
   - **Requests**: Handles HTTP requests for APIs like Open-Meteo and API Ninjas.
   - **YAML**: Loads configuration settings.
   - **Logging**: Manages logging throughout the script.
   - **Asyncio**: Supports asynchronous operations for timers and reminders.
   - **Playsound**: Plays audio files.
   - **Google and Spotify Agents**: Custom modules for interacting with Google Calendar and Spotify.

2. **Configuration Loading**:
   - `_load_config()`: Loads settings from a `config.yaml` file, which includes API keys and other configuration details.

3. **Classes and Their Responsibilities**:

   - **TextToSpeech**:
     - Wraps the ElevenLabs API for speech synthesis.
     - Initializes with configuration settings and generates audio from text.
     - Plays generated audio using `playsound`.

   - **GPTClient**:
     - Interacts with OpenAI's GPT models.
     - Retrieves text responses for given conversations.
     - Selects animations based on conversation context.
     - Manages emotion counters to track and vary emotional responses.

   - **Functions**:
     - Executes workflows by invoking various tools and functions.
     - Integrates with Google and Spotify agents to handle specific requests.
     - Provides utility functions like setting timers, getting weather information, and managing reminders.

4. **Notable Algorithms and Logic**:
   - **Emotion Counter**: Tracks the frequency of emotions used in responses to ensure varied interactions.
   - **Weather Retrieval**: Uses Open-Meteo API to fetch current weather and forecasts, interpreting weather codes for human-readable descriptions.
   - **Timer and Reminder Scheduling**: Utilizes asyncio to schedule and manage timers and reminders asynchronously.
   - **Workflow Execution**: Dynamically executes a series of tool calls suggested by GPT, handling each tool's specific logic.

5. **External API Interactions**:
   - **OpenAI**: For generating conversational responses and selecting animations.
   - **ElevenLabs**: For converting text to speech.
   - **Open-Meteo**: For fetching weather data.
   - **API Ninjas**: For retrieving random advice.
   - **Google Calendar and Spotify**: Through custom agents for managing calendar events and Spotify interactions.

6. **Error Handling**:
   - The script includes error handling for API calls and file operations, logging errors where appropriate.

7. **Main Execution**:
   - If run as a standalone script, it initializes a `GoogleCalendarManager` to print calendars and upcoming events.

### Configuration and Setup
- The script requires a `config.yaml` file containing API keys and settings for ElevenLabs, OpenAI, and other services.
- External modules like `google_agent` and `spotify_agent` need to be available for full functionality.

This script is designed to be part of a larger system, likely integrated into an assistant application, providing a robust framework for handling various AI-driven tasks.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\llm_client_utils.py
The Python script is a utility module designed for a Language Model (LLM) client, providing shared functions and tool definitions. Its primary purpose is to facilitate various functionalities such as fetching jokes, quotes, city coordinates, and managing animations and tools for the LLM client.

### Main Components

1. **Weather Code Descriptions**: A dictionary mapping weather codes to human-readable descriptions, useful for interpreting weather data.

2. **Configuration Loader**:
   - **_load_config()**: This function loads a YAML configuration file located in a parent directory. It retrieves settings such as API keys, which are essential for making authenticated requests to external services.

3. **External API Interactions**:
   - **get_joke()**: Fetches a random joke from the "Official Joke API". It constructs a joke string from the API response.
   - **get_quote()**: Retrieves a motivational quote from the "API Ninjas" service using an API key from the configuration.
   - **get_city_coordinates(city)**: Obtains latitude and longitude for a specified city using the "API Ninjas" service, again requiring an API key.

4. **Tool Definitions**:
   - **set_animation_tool**: A predefined tool for setting animations based on emotional states. It includes a list of possible animations and describes how the bot should choose one based on context.
   - **build_tools()**: Constructs a list of tool definitions, each represented as a dictionary. These tools include:
     - Web search preview configuration.
     - Weather information retrieval.
     - Joke and quote fetching.
     - City coordinates lookup.
     - Advice retrieval.
     - Google and Spotify service interactions.
     - Timer and reminder settings.
     - Daily summary generation.

### Structure and Interaction

- The script is organized into utility functions and tool definitions, which are used by the LLM client to perform specific tasks.
- Functions like `get_joke`, `get_quote`, and `get_city_coordinates` rely on external APIs, requiring network access and valid API keys from the configuration file.
- The `build_tools` function aggregates various tool definitions, potentially used by the LLM client to decide which actions to perform based on user input or context.

### External Dependencies

- **os** and **yaml**: For file path manipulation and configuration loading.
- **requests**: To make HTTP requests to external APIs.
- **datetime**: For time-related operations, such as formatting current time and day.

### Notable Logic

- The script uses a configuration file to manage API keys and settings, ensuring secure and flexible access to external services.
- It defines a comprehensive set of tools that can be dynamically utilized by the LLM client, allowing for a wide range of interactions and functionalities, from fetching jokes to setting reminders.

### Configuration Requirements

- A YAML configuration file (`config.yaml`) is required, containing API keys and other settings necessary for API interactions and tool configurations.

Overall, this script serves as a backend utility module for an LLM client, enabling it to perform various tasks through well-defined functions and tools.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\spotify_agent.py
The Python script `spotify_agent.py` is designed to interact with Spotify's API to perform various music-related tasks. It acts as an agent that can execute commands based on user input, leveraging Spotify's features and integrating with OpenAI's language model for decision-making.

### Overall Purpose
The script provides a command-line interface for users to interact with Spotify. It allows users to search for tracks, manage playback, queue songs, list devices, and more. The script uses OpenAI's language model to interpret user requests and decide which Spotify tool to invoke.

### Main Components

#### Classes and Functions

1. **SpotifyAgent Class**
   - **Purpose**: Acts as the main interface for handling Spotify-related tasks.
   - **Methods**:
     - `_load_config`: Loads configuration settings from a YAML file, including API keys and model settings.
     - `__init__`: Initializes the agent, setting up the Spotify handler and OpenAI API key.
     - `_dispatch`: Maps function names to specific Spotify actions, executing them with provided arguments.
     - `llm_decide_and_dispatch`: Uses OpenAI's language model to decide which Spotify tool to use based on user input.

2. **_pretty Function**
   - **Purpose**: Formats and prints the output of Spotify actions in a human-readable way.

3. **Main Execution Block**
   - **Purpose**: Provides a command-line interface for user interaction. It continuously prompts the user for input, processes the request, and displays the result.

### Structure and Interaction
- The script defines a set of tools (`SPOTIFY_TOOLS`) that represent different Spotify actions, such as searching for tracks, managing playback, and listing devices.
- The `SpotifyAgent` class is the core component, responsible for loading configurations, interacting with Spotify through the `SpotifyHA` utility, and using OpenAI to interpret user requests.
- The `_dispatch` method handles the execution of specific Spotify actions based on the tool name and arguments provided.
- The `llm_decide_and_dispatch` method constructs a message for OpenAI's language model, which decides which tool to invoke based on the user's request.

### External Dependencies
- **SpotifyHA**: A utility for interacting with Spotify's API. It must be imported from either `spotify_ha_utils` or `llm.spotify_ha_utils`.
- **OpenAI API**: Used for natural language processing to interpret user requests and decide on actions.
- **YAML**: Used for configuration management, loading API keys, and model settings.

### Configuration Requirements
- A configuration file (`config.yaml`) is required, containing OpenAI API keys and model settings.
- The script expects the configuration file to be located in a `config` directory relative to the script's parent directory.

### Notable Algorithms and Logic
- **Decision Making with LLM**: The script uses OpenAI's language model to interpret user input and decide which Spotify tool to execute. This involves constructing a message with available tools and current context, then parsing the model's response to determine the appropriate action.
- **Dispatch Mechanism**: The `_dispatch` method maps tool names to specific Spotify actions, handling argument parsing and execution logic for each tool.

Overall, the script provides a robust interface for interacting with Spotify, leveraging AI to enhance user interaction and automate music management tasks.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\spotify_ha_utils.py
### Overview

The script `spotify_ha_utils.py` is a utility for interacting with Spotify's API, focusing on queue and playback management. It provides a command-line interface (CLI) with optional pretty-printing using the `Rich` library. The script includes features for searching and queuing tracks, managing playback, and handling playlists.

### Main Components

#### External Dependencies

- **Spotipy**: A lightweight Python library for the Spotify Web API, used for authentication and API requests.
- **PyYAML**: Used for loading configuration files.
- **Rich** (optional): Used for enhanced CLI output with tables and formatted text.

#### Configuration

- The script requires a configuration file (`config.yaml`) containing Spotify API credentials (`spotify_client_id` and `spotify_client_secret`).

### Key Classes and Functions

#### `SpotifyHA` Class

This is the core class providing an object-oriented interface to Spotify's API. It encapsulates various functionalities related to playback and queue management.

- **Initialization**: Authenticates with Spotify using credentials from a configuration file. It sets up an instance of `spotipy.Spotify` with the necessary scopes for reading and modifying playback.

- **Helper Methods**:
  - `_flat`: Simplifies track information into a dictionary with key details like name, artists, and duration.
  - `_ms_to_mmss`: Converts milliseconds to a `MM:SS` format for display.
  - `_fmt_track`: Formats track information for display.

- **Playback Methods**:
  - `get_current_playback`, `get_current_track`, `is_playing`: Retrieve current playback status and track information.
  - `play`, `pause`, `skip_next`, `skip_previous`, `toggle_play_pause`: Control playback on a specified or active device.
  - `transfer_playback`: Transfers playback to a different device.

- **Queue Management**:
  - `get_queue`: Retrieves the current queue.
  - `add_to_queue`: Adds a track to the queue, with optional verification.
  - `remove_from_queue`: Precisely removes a track from the queue by skipping and re-queuing tracks.

- **Search and Queue**:
  - `search_tracks`: Searches for tracks based on a query.
  - `search_and_queue_track`: Searches for tracks and queues one, either the first result or a random choice.

- **Artist and Album Helpers**:
  - `artist_top_track`: Finds and queues a top track from a specified artist.
  - `play_album_by_name`: Searches for an album by name (and optional artist) and starts playback.

- **Playlist and History**:
  - `save_current_track_to_playlist`: Saves the currently playing track to a specified playlist.
  - `get_recently_played`: Retrieves recently played tracks.

- **CLI Demo**:
  - `demo`: Demonstrates the utility's capabilities by queuing a track and displaying the queue with estimated times. Uses `Rich` if available for enhanced output.

### Notable Logic

- **Queue Management**: The script includes logic to manage the queue precisely by skipping tracks and re-queuing them to maintain order after a removal.
- **Artist Selection**: Implements a method to select the best matching artist based on the query or popularity.
- **CLI Output**: Utilizes the `Rich` library for a visually appealing command-line interface, displaying track information and queue status in a formatted table.

### Execution

The script includes a demo execution block that runs if the script is executed directly. It demonstrates the functionality by queuing a track from "Kaizers Orchestra" and displaying the queue.

Overall, the script provides a comprehensive tool for managing Spotify playback and queue through a Python interface, with optional CLI enhancements for user interaction.
