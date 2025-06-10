# Detailed Event Flow

The Wheatley assistant relies on an asynchronous event loop. This document explains how events are created, processed, and how each subsystem cooperates. The visualization is deliberately verbose so new contributors can trace every step of execution.

## Life of an Event

1. **User or External Trigger**
   - Terminal input, hotword transcription, timers, or hardware feedback create an event object.
2. **Queue Insertion**
   - All events are placed onto a central `asyncio.Queue` in `main.py`.
3. **Retrieval**
   - The `async_conversation_loop` waits on the queue and pulls events one at a time.
4. **Processing**
   - `process_event` appends the event to `ConversationManager` and checks for an exit condition.
5. **LLM Interaction**
   - `GPTClient` uses the latest conversation to produce a response and optional tool workflow.
6. **Tool Workflow**
   - Tools run via `Functions.execute_workflow`, pushing further events like timer expirations.
7. **TTS & Hardware**
   - The response text is spoken by `TextToSpeechEngine`. Hardware animations are triggered in parallel.
8. **Follow-up Listening**
   - If enabled, `SpeechToTextEngine` listens without a hotword for a short time to capture follow-up commands.

## Comprehensive Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant MIC as Microphone
    participant STT as STT Engine
    participant Q as Event Queue
    participant LOOP as async_conversation_loop
    participant CM as ConversationManager
    participant LLM as GPTClient
    participant TTS as TTS Engine
    participant HW as ArduinoInterface

    U->>MIC: speak
    MIC->>STT: audio frames
    STT->>Q: Event(text)
    LOOP->>Q: await event
    Q-->>LOOP: Event(text)
    LOOP->>CM: update history
    LOOP->>LLM: current conversation
    LLM-->>LOOP: reply & workflow
    LOOP->>CM: store assistant text
    LOOP->>TTS: speak reply
    TTS->>HW: start animation
    TTS->>U: audio
    HW-->>U: movement & LEDs
    LOOP->>STT: optional follow-up listening
```

Events from timers or external integrations follow the exact same path. The queue acts as the glue that allows independent producers and consumers to operate without blocking each other.

