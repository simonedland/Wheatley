# AI Codebase Overview

Certainly! Here is a **detailed summary and analysis** of the provided `llm_client.py` script, focusing on its **purpose, structure, main classes/functions, dependencies, configuration, and notable logic**.

---

## **Overall Purpose**

The script serves as the **central integration layer for an AI assistant** ("Wheatley"), orchestrating:

- Interactions with OpenAI's GPT models (LLMs)
- Text-to-speech (TTS) via ElevenLabs
- External APIs (Google Calendar, Spotify, weather, advice, etc.)
- Tool invocation and workflow execution (timers, reminders, jokes, etc.)
- Persistent long-term memory management

It enables the assistant to process user input, decide when to call external tools, synthesize speech, and manage complex, multi-step conversational workflows.

---

## **Main Components and Structure**

### **1. TextToSpeech Class**

**Purpose:**  
Encapsulates ElevenLabs TTS API for generating and playing speech.

**Responsibilities:**
- Loads TTS configuration from `config.yaml`
- Generates speech audio from text using ElevenLabs
- Plays audio using `playsound`, managing temporary files
- Can reload configuration at runtime

**Notable Logic:**
- Uses a temp directory for audio files, cleans up after playback
- Logs timing for TTS generation and playback
- Supports dynamic reloading of voice/personality settings

---

### **2. GPTClient Class**

**Purpose:**  
Handles all interactions with OpenAI’s GPT models, including standard conversation and tool invocation.

**Responsibilities:**
- Loads OpenAI API key and model from config
- Sends conversation history to GPT and extracts the assistant’s reply
- Asks GPT to select an animation/mood, using an emotion counter to encourage variety
- Builds and sends tool invocation requests to GPT, supporting parallel tool calls
- Tracks and persists emotion usage to encourage diverse responses

**Notable Logic:**
- Dynamically adjusts tool prompts/context based on emotion usage
- Handles both standard text and tool-calling workflows
- Persists emotion usage in a JSON file for continuity

---

### **3. Functions Class**

**Purpose:**  
Implements the actual logic for the “tools” that GPT can invoke.

**Responsibilities:**
- Initializes sub-agents (Google, Spotify) based on config/service status
- Executes workflows: iterates over tool calls suggested by GPT, dispatches to the relevant function, and collects results
- Provides implementations for:
  - Google/Spotify agent calls
  - Timer and reminder scheduling (with async event queue support)
  - Weather queries (via Open-Meteo API)
  - Jokes, quotes, advice (via utility functions or external APIs)
  - City coordinate lookup
  - Daily summary (combines calendar, weather, and quote)
  - Personality switching (updates config and TTS settings)
  - Persistent memory (read, write, edit)

**Notable Logic:**
- Uses async scheduling for timers and reminders
- Supports event queue integration for real-time assistant events
- Handles fallback and error cases for unavailable services
- Allows dynamic personality switching by updating config and TTS

---

### **4. Utility Imports and Functions**

- **From `llm_client_utils`:**  
  Weather code descriptions, joke/quote fetchers, city coordinate lookup, tool builders, config loader
- **From `utils.timing_logger`:**  
  For performance measurement
- **From `utils.long_term_memory`:**  
  For persistent assistant memory

---

## **External Dependencies and APIs**

- **OpenAI GPT API:**  
  For all LLM-based conversation and tool selection
- **ElevenLabs API:**  
  For text-to-speech synthesis
- **Google Calendar API:**  
  Via `GoogleCalendarManager` and `GoogleAgent`
- **Spotify API:**  
  Via `SpotifyAgent`
- **Open-Meteo API:**  
  For weather data
- **API Ninjas:**  
  For random advice
- **Other:**  
  `playsound` for audio playback, `requests` for HTTP, `yaml` and `json` for config/data

---

## **Configuration Requirements**

- **`config.yaml`:**  
  Must exist in a `config` directory two levels up from this script. Contains:
  - API keys (OpenAI, ElevenLabs, API Ninjas, etc.)
  - TTS settings (voice, model, etc.)
  - Assistant personalities and system messages
  - Web search settings (optional)
- **Emotion counter JSON:**  
  Used to persist emotion/mood usage for animation selection
- **Long-term memory JSON:**  
  Used for persistent assistant memory

---

## **Code Structure and Interactions**

- **Assistant workflow:**
  1. **User input** is processed and sent to `GPTClient`
  2. **GPTClient** determines if a tool call is needed, or generates a reply
  3. If tools are invoked, **Functions** executes them (possibly using Google/Spotify agents, weather APIs, etc.)
  4. **TextToSpeech** is used to vocalize summaries or actions
  5. **Event queue** is used for timers/reminders, integrating with the assistant’s event loop
  6. **Persistent memory** is managed via utility functions

- **Modularity:**  
  Each external service is abstracted behind a class or utility, allowing for easier extension and maintenance

---

## **Notable Algorithms and Logic**

- **Emotion Counter:**  
  Tracks which moods/animations have been used, and biases GPT to select less-used ones for variety
- **Dynamic Tool Context:**  
  System messages and tool descriptions are dynamically adjusted based on conversation state and emotion usage
- **Async Scheduling:**  
  Uses asyncio for timers and reminders, posting events to an event queue
- **Personality Switching:**  
  Updates both system messages and TTS settings on the fly, allowing the assistant to change “character”

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