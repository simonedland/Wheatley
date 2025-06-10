# Project Architecture Overview

This document explains the main components that power the Wheatley assistant and how they work together.

## High-Level Components

1. **Speech to Text (STT)**
   - Implemented in `stt/stt_engine.py`.
   - Uses Porcupine for hotword detection, then records speech until silence and transcribes the result with Whisper.
2. **Conversation Manager**
   - Located in `assistant/assistant.py`.
   - Keeps a bounded history of system and user messages for context.
3. **Large Language Model (LLM)**
   - Accessed through `llm/llm_client.py`.
   - Handles calls to the OpenAI API and provides workflow utilities.
4. **Text to Speech (TTS)**
   - Provided by `tts/tts_engine.py`.
   - Converts assistant responses into audio using the ElevenLabs API.
5. **Hardware Interface**
   - Managed by `hardware/arduino_interface.py`.
   - Controls servos and LED animations on the connected Arduino board.

## Execution Flow

`main.py` ties all components together. When started it:

1. Loads configuration from `config/config.yaml`.
2. Initialises STT, TTS, the LLM client and the Arduino interface.
3. Prints an ASCII welcome banner and an initial greeting from the assistant.
4. Enters an asynchronous loop that:
   - Waits for user input via text or the hotword listener.
   - Sends the conversation to the LLM for processing and tool calls.
   - Executes any returned workflow functions.
   - Plays the assistant response and triggers an animation.

The loop continues until the user types or says "exit", after which resources are cleaned up and the program terminates.

## Additional Utilities

- `install_prerequisites.py` installs packages listed in `requirements.txt`.
- `docs/tts_and_hotword_flow.md` details how speech synthesis and hotword detection operate.
- `old_inspiration.py` contains prototype code kept for reference.

This structure keeps the codebase modular so that each part of the assistant can be developed or replaced independently.
