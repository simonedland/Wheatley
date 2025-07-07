```mermaid
---
config:
  layout: dagre
  look: classic
  theme: neutral
---
flowchart TD
  Main[main.py: CLI entry point and async event loop orchestrator]
  Assistant[assistant.py: ConversationManager - manages conversation history]
  Arduino[arduino_interface.py: ArduinoInterface/ServoController - controls hardware servos and LEDs]
  LLMClient[llm_client.py: GPTClient/Functions/TextToSpeech - LLM, tools, TTS]
  TTS[tts_engine.py: TextToSpeechEngine - ElevenLabs TTS streaming/playback]
  STT[stt_engine.py: SpeechToTextEngine - Speech-to-text, hotword detection]
  GoogleAgent[google_agent.py: GoogleAgent/GoogleCalendarManager - Google Calendar tools]
  SpotifyAgent[spotify_agent.py: SpotifyAgent - Spotify LLM agent/tools]
  SpotifyHA[spotify_ha_utils.py: SpotifyHA - Spotipy playback/queue utils]
  LongTermMemory[long_term_memory.py: Persistent JSON memory store]
  TimingLogger[timing_logger.py: Timing logger for performance metrics]
  MainHelpers[main_helpers.py: Feature summary and service auth helpers]
  ServiceAuth[service_auth.py: External service authentication]
  LLMUtils[llm_client_utils.py: LLM tool definitions/utilities]
  Test[test.py: Unit tests for LLM and TTS]
  PoC[PoC.py: LLM-to-TTS streaming with live table UI (demo)]
  AdNauseam[ad_nauseam.py: Code summarizer using OpenAI API]
  Puppet[puppet.py: Servo/LED GUI for hardware puppet]
  Timeline[present_timeline.py: GUI for timing/log visualization]
  InstallReq[install_prerequisites.py: Installs Python requirements]

  Main --> Assistant
  Main --> Arduino
  Main --> LLMClient
  Main --> TTS
  Main --> STT
  Main --> MainHelpers
  Main --> TimingLogger

  Assistant --> LongTermMemory
  Assistant --> TimingLogger

  Arduino --> ServoController[ServoController: Animations, servo config]
  Arduino --> TimingLogger

  LLMClient --> LLMUtils
  LLMClient --> GoogleAgent
  LLMClient --> SpotifyAgent
  LLMClient --> LongTermMemory
  LLMClient --> TimingLogger
  LLMClient --> TTS

  TTS --> TimingLogger

  STT --> Arduino
  STT --> TimingLogger

  GoogleAgent --> GoogleCalendarManager[GoogleCalendarManager: Google Calendar API]
  GoogleAgent --> TimingLogger

  SpotifyAgent --> SpotifyHA
  SpotifyAgent --> TimingLogger

  MainHelpers --> ServiceAuth

  ServiceAuth --> GoogleAgent
  ServiceAuth --> SpotifyAgent

  Test --> LLMClient
  Test --> TTS

  PoC --> TTS
  PoC --> LLMClient

  AdNauseam --> LLMClient
  AdNauseam --> TimingLogger

  Puppet --> Arduino

  Timeline --> TimingLogger

  InstallReq -.->|Runs before all| Main

  subgraph Hardware
    Arduino
    Puppet
  end

  subgraph LLM
    LLMClient
    LLMUtils
    GoogleAgent
    SpotifyAgent
    SpotifyHA
  end

  subgraph Audio
    TTS
    STT
    PoC
  end

  subgraph Utils
    TimingLogger
    LongTermMemory
    MainHelpers
    ServiceAuth
  end

  subgraph GUI
    Puppet
    Timeline
  end

  subgraph CLI
    Main
    AdNauseam
    InstallReq
    Test
  end
```
