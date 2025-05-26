# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\google_agent.py
The Python code defines a system for managing Google Calendar events using a combination of Google APIs and OpenAI's language model. It consists of two main classes: `GoogleCalendarManager` and `GoogleAgent`.

1. **GoogleCalendarManager**:
   - **Purpose**: Manages interactions with Google Calendar.
   - **Initialization**: Loads configuration from a YAML file and sets up Google API credentials.
   - **Methods**:
     - `get_google_credentials`: Retrieves and refreshes Google API credentials.
     - `list_calendars`: Lists available calendars, excluding those specified in the configuration.
     - `get_upcoming_events`: Fetches upcoming events from the calendars for a specified number of days.
     - `print_calendars` and `print_upcoming_events`: Prints the list of calendars and upcoming events, respectively.

2. **GoogleAgent**:
   - **Purpose**: Acts as an interface between user requests and Google Calendar functions, utilizing OpenAI's language model to decide which action to take.
   - **Initialization**: Loads configuration, including OpenAI API key, and initializes `GoogleCalendarManager`.
   - **Methods**:
     - `llm_decide_and_dispatch`: Uses OpenAI's model to determine which calendar function to execute based on user input.
     - `dispatch`: Executes the chosen calendar function.
     - `get_google_calendar_events`: Retrieves upcoming events via `GoogleCalendarManager`.

3. **Google Tools**: Defines placeholder functions for interacting with Google Calendar, such as getting, creating, and deleting events.

Overall, the code is designed to automate the management of Google Calendar events based on user requests, leveraging AI to determine the appropriate actions.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\llm_client.py
This Python code is designed to interact with various APIs and services, primarily focusing on text-to-speech (TTS), OpenAI's GPT models, and several utility functions. Here's a summary of its purpose and logic:

1. **Configuration Loading**: The code loads configuration settings from a YAML file, which includes API keys and other parameters for different services.

2. **Text-to-Speech (TTS)**: It uses the ElevenLabs API to convert text to speech. The `TextToSpeech` class manages TTS settings and audio generation. It can generate and play audio files using specified voice settings.

3. **GPT Client**: The `GPTClient` class interacts with the OpenAI API to generate text responses based on input conversations. It also manages mood tracking and emotion counters to influence response styles.

4. **Function Execution**: The `Functions` class handles executing various predefined functions, such as getting weather data, jokes, quotes, reversing text, and more. It uses external APIs to fetch data and responds accordingly.

5. **Tool and Workflow Management**: The code dynamically builds a list of tools and functions that can be executed based on user input. It supports calling Google and Spotify agents for related tasks.

6. **Weather and Utility Functions**: It includes functions to fetch weather information, jokes, quotes, city coordinates, and advice using external APIs.

7. **Logging and Error Handling**: The code includes logging for monitoring execution times and error handling to manage exceptions during API calls and file operations.

8. **Main Execution**: The script's main section initializes a `GoogleCalendarManager` to print calendars and upcoming events, demonstrating integration with Google services.

Overall, the code is structured to provide a flexible interface for interacting with various APIs, enabling text generation, TTS, and utility functions through a command-driven approach.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\spotify_agent.py
The Python code defines a `SpotifyAgent` class that integrates with Spotify's API to provide various functionalities for managing music playback. It includes tools for searching tracks, queuing songs, retrieving recently played tracks, listing devices, transferring playback between devices, and playing albums. The agent uses OpenAI's API to interpret user requests and decide which Spotify tool to execute. The code handles user input in a loop, dispatching the appropriate function based on the request and returning the results in a user-friendly format. The agent is designed to work for a Norwegian market and supports various playback and queue management operations.

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\llm\spotify_ha_utils.py
This Python script is a utility for interacting with Spotify's API, focusing on queue and playback management. It uses the Spotipy library to handle authentication and API requests. The script includes features such as:

1. **Configuration Loading**: It reads configuration details, including Spotify API credentials, from a YAML file.

2. **Playback Control**: It provides methods to control playback, such as play, pause, skip, and transfer playback to different devices.

3. **Queue Management**: It allows adding tracks to the queue, removing specific tracks, and retrieving the current queue with estimated wait times.

4. **Track and Artist Search**: It includes functions to search for tracks and artists, automatically select the best match, and queue or play tracks.

5. **Playlist and History Management**: It can save the currently playing track to a playlist and retrieve recently played tracks.

6. **Album Playback**: It can search for an album by name and start playback.

7. **Command-Line Interface (CLI) Demo**: If the Rich library is available, it provides a pretty CLI demo with a table display of the queue and estimated times.

The script is designed to be run as a standalone program, demonstrating its capabilities by queuing a track from a specified artist.
