# Code Logic

## Entry Points

- **`main.py`** – launched via CLI to start the assistant. It loads `config.yaml` and initializes all subsystems.
- **`puppet.py`** – optional GUI for direct servo control.
- **`.ino` sketches** – flashed onto microcontrollers and run on boot.

## Inter-Script Communication

1. `main.py` imports and instantiates:
   - `SpeechToTextEngine` from `stt/stt_engine.py`
   - `GPTClient` and `Functions` from `llm/llm_client.py`
   - `TextToSpeechEngine` from `tts/tts_engine.py`
   - `ArduinoInterface` from `hardware/arduino_interface.py`
2. `GPTClient` triggers tool calls which are dispatched through `Functions.execute_workflow()`. Results are added back to the conversation.
3. The `SpeechToTextEngine` pushes voice events into an async queue consumed by `main.py`.
4. `ArduinoInterface` sends serial commands to the M5Stack; it also exposes servo state to other modules.

## Data Contracts

- **STT Events**: `{"type": "voice", "text": "..."}` placed onto the async queue.
- **LLM Tools**: list of `{"name": str, "arguments": {...}}` items returned by `GPTClient.get_workflow()`.
- **Servo Config Command**: `SET_SERVO_CONFIG:id,target,velocity,idle_range,interval;...` sent as text lines.
- **Audio Files**: temporary `.mp3` created by `TextToSpeechEngine` and deleted after playback.

## Control Flow

```
+-----------------------+
|  user_input_producer  |
+-----------+-----------+
            |
            v
+-----------+-----------+
|    async queue        |
+-----------+-----------+
            |
            v
+-----------+-----------+
|  main async loop      |
+-----------+-----------+
   |       |        |
   |       |        +--> GPTClient -> Tools -> ArduinoInterface
   |       +--> TextToSpeechEngine
   +--> SpeechToTextEngine
```

Error handling includes retries when querying the LLM and validation of servo ranges before sending commands. When hardware is unavailable, `ArduinoInterface` runs in dry-run mode to avoid crashes.
