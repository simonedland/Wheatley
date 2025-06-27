```mermaid
---
config:
  layout: dagre
  look: classic
  theme: neutral
---
flowchart TD
  Main[main.py: Main event loop and orchestrator for Wheatley assistant]
  load_config[load_config: Loads YAML configuration]
  initialize_assistant[initialize_assistant: Instantiates all subsystems (LLM, TTS, STT, Arduino, etc.)]
  Event[Event: Dataclass for event objects in async loop]
  async_conversation_loop[async_conversation_loop: Handles async event-driven conversation]
  user_input_producer[user_input_producer: Produces user input events]
  print_event[print_event: Prints event objects]
  get_event[get_event: Retrieves and normalizes events from queue]
  handle_non_user_event[handle_non_user_event: Adds system messages for non-user events]
  process_event[process_event: Updates conversation and checks for exit]
  run_tool_workflow[run_tool_workflow: Executes LLM-suggested tool workflow]
  generate_assistant_reply[generate_assistant_reply: Gets LLM reply and animation]
  handle_tts_and_follow_up[handle_tts_and_follow_up: Plays TTS and manages follow-up input]
  print_async_tasks[print_async_tasks: Prints list of async tasks]
  ConversationManager[ConversationManager: Maintains bounded conversation history]
  GPTClient[GPTClient: Handles OpenAI LLM API interactions]
  Functions[Functions: Implements LLM tool functions]
  TextToSpeechEngine[TextToSpeechEngine: ElevenLabs TTS and playback]
  SpeechToTextEngine[SpeechToTextEngine: Handles hotword detection and speech-to-text]
  ArduinoInterface[ArduinoInterface: Controls Arduino-based servo hardware]
  ServoController[ServoController: Manages servo configs and emotion animations]
  Servo[Servo: Represents a single servo motor]
  service_auth[service_auth.py: Authenticates external services and provides agents]
  authenticate_services[authenticate_services: Checks and prints service status]
  GoogleAgent[GoogleAgent: LLM-driven Google Calendar agent]
  GoogleCalendarManager[GoogleCalendarManager: Interacts with Google Calendar API]
  SpotifyAgent[SpotifyAgent: LLM-driven Spotify agent]
  SpotifyHA[SpotifyHA: Spotipy-based Spotify control and queue]
  timing_logger[timing_logger.py: Captures and exports execution timings]
  record_timing[record_timing: Records timing entries]
  export_timings[export_timings: Writes timings to file]
  clear_timings[clear_timings: Clears timing log]
  long_term_memory[long_term_memory.py: Persistent JSON-based storage]
  read_memory[read_memory: Reads memory entries]
  overwrite_memory[overwrite_memory: Overwrites memory file]
  edit_memory[edit_memory: Edits or appends memory entries]
  llm_client_utils[llm_client_utils.py: Shared utilities and tool definitions for LLM]
  build_tools[build_tools: Builds LLM tool list]
  get_joke[get_joke: Fetches a random joke]
  get_quote[get_quote: Fetches a motivational quote]
  get_city_coordinates[get_city_coordinates: Gets city coordinates]
  present_timeline[present_timeline.py: GUI for displaying timing and log data]
  TimelineGUI[TimelineGUI: Tkinter GUI for timeline and logs]
  puppet[puppet.py: GUI for servo control and calibration]
  PuppetGUI[PuppetGUI: Tkinter GUI for servo puppet]
  SerialBackend[SerialBackend: Serial communication for puppet GUI]
  install_prerequisites[install_prerequisites.py: Installs Python requirements]
  old_inspiration[old_inspiration.py: ElevenLabs TTS streaming demo]
  test[test.py: Unit tests for main modules]

  Main --> load_config
  Main --> initialize_assistant
  Main --> async_conversation_loop
  Main --> print_async_tasks
  Main --> clear_timings
  Main --> export_timings
  Main --> authenticate_services
  Main --> ConversationManager
  Main --> GPTClient
  Main --> TextToSpeechEngine
  Main --> SpeechToTextEngine
  Main --> ArduinoInterface

  initialize_assistant --> ConversationManager
  initialize_assistant --> GPTClient
  initialize_assistant --> TextToSpeechEngine
  initialize_assistant --> SpeechToTextEngine
  initialize_assistant --> ArduinoInterface
  ArduinoInterface --> ServoController
  ServoController --> Servo

  async_conversation_loop --> user_input_producer
  async_conversation_loop --> get_event
  async_conversation_loop --> process_event
  async_conversation_loop --> run_tool_workflow
  async_conversation_loop --> generate_assistant_reply
  async_conversation_loop --> handle_tts_and_follow_up
  async_conversation_loop --> print_event
  async_conversation_loop --> print_async_tasks
  async_conversation_loop --> ArduinoInterface

  user_input_producer --> Event
  get_event --> Event
  process_event --> ConversationManager
  process_event --> handle_non_user_event
  handle_non_user_event --> ConversationManager
  run_tool_workflow --> GPTClient
  run_tool_workflow --> Functions
  run_tool_workflow --> ConversationManager
  run_tool_workflow --> timing_logger
  generate_assistant_reply --> GPTClient
  generate_assistant_reply --> ConversationManager
  generate_assistant_reply --> ArduinoInterface
  handle_tts_and_follow_up --> TextToSpeechEngine
  handle_tts_and_follow_up --> SpeechToTextEngine
  handle_tts_and_follow_up --> Event

  GPTClient --> llm_client_utils
  GPTClient --> timing_logger
  GPTClient --> Functions
  GPTClient --> TextToSpeechEngine
  GPTClient --> GoogleAgent
  GPTClient --> SpotifyAgent

  Functions --> GPTClient
  Functions --> GoogleAgent
  Functions --> SpotifyAgent
  Functions --> timing_logger
  Functions --> long_term_memory
  Functions --> llm_client_utils

  TextToSpeechEngine --> timing_logger

  SpeechToTextEngine --> timing_logger
  SpeechToTextEngine --> ArduinoInterface

  ArduinoInterface --> ServoController
  ArduinoInterface --> Servo

  service_auth --> authenticate_services
  authenticate_services --> GoogleAgent
  authenticate_services --> SpotifyAgent

  GoogleAgent --> GoogleCalendarManager
  GoogleAgent --> GPTClient

  SpotifyAgent --> SpotifyHA

  timing_logger --> record_timing
  timing_logger --> export_timings
  timing_logger --> clear_timings

  long_term_memory --> read_memory
  long_term_memory --> overwrite_memory
  long_term_memory --> edit_memory

  llm_client_utils --> build_tools
  llm_client_utils --> get_joke
  llm_client_utils --> get_quote
  llm_client_utils --> get_city_coordinates

  present_timeline --> TimelineGUI
  TimelineGUI --> timing_logger

  puppet --> PuppetGUI
  PuppetGUI --> SerialBackend

  install_prerequisites -->|Runs| None
  old_inspiration -->|Demo| None
  test --> Main
  test --> ConversationManager
  test --> GPTClient
  test --> TextToSpeechEngine
  test --> SpeechToTextEngine
  test --> ArduinoInterface
  test --> long_term_memory
```
