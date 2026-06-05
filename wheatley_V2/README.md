# Wheatley V2

A fast, simple voice assistant. V2 is a ground-up redesign of V1 with three goals:

1. **Simple** — a flat package, one small single-purpose file per concern, each
   readable top-to-bottom. No agent framework, no MCP subprocess servers.
2. **Fast** — minimize the time from the user speaking/typing until they hear a
   reply, by streaming and overlapping stages.
3. **Cheap to reason about** — leaf modules depend only on stdlib + external
   libraries. They never import sibling `wheatley_V2` modules. Only `main.py`
   wires things together (dependency injection).

STT and the LLM run on [OpenRouter](https://openrouter.ai); TTS stays on
[ElevenLabs](https://elevenlabs.io).

## Architecture

```
                 mic / keyboard
                      |
            +---------v---------+
            |   stt.py          |  VoiceListener: wake word -> record ->
            | (VoiceListener)   |  OpenRouter STT (Whisper)
            +---------+---------+
                      | text
            +---------v---------+
            | conversation.py   |  ConversationManager: holds history,
            | (ConversationMgr) |  runs the LLM <-> tool loop
            +----+----+----+----+
                 |    |    |
        chat_stream   |    |  tool calls (dispatch)
                 |    |    |
       +---------v-+  |  +-v-----------------------------+
       | openrouter |  |  | memory.py     MEMORY_TOOLS    |
       | .chat_     |  |  | personality.py PERSONALITY_.. |
       |  stream    |  |  | tools.py       SIMPLE_TOOLS   |
       | .transcribe|  |  | integrations.py INTEGRATION_..|
       +-----------+  |  | hardware.py    ANIMATION_TOOLS |
                      |  +------------------------------+
              token stream
                      |
            +---------v---------+
            |    tts.py         |  TTSHandler: streams ElevenLabs audio as
            | (TTSHandler)      |  sentences arrive (no full-reply buffering)
            +---------+---------+
                      |
                   speaker
```

`main.py` is the orchestrator: it loads `Settings`, constructs each component,
injects dependencies, and runs the listen -> think -> speak loop.

## Modules

| File | Responsibility | Public surface (contract) |
|------|----------------|---------------------------|
| `config.py` | Load secrets (`.env`) + config (`config.yaml`) | `Settings`, `load_settings()`, `get_secret()` |
| `openrouter.py` | One HTTP client for LLM + STT on OpenRouter | `OpenRouterClient.chat_stream`, `.transcribe` |
| `stt.py` | Wake word, record, transcribe | `VoiceListener` |
| `tts.py` | Stream speech from ElevenLabs | `TTSHandler` |
| `conversation.py` | History + LLM/tool loop | `ConversationManager` |
| `memory.py` | Long-term memory tools | `MEMORY_TOOLS`, `dispatch` |
| `personality.py` | Switch/describe personalities | `PERSONALITY_TOOLS`, `dispatch` |
| `tools.py` | Simple built-in tools (time, etc.) | `SIMPLE_TOOLS`, `dispatch` |
| `integrations.py` | Spotify, Google Calendar, etc. | `INTEGRATION_TOOLS`, `dispatch` |
| `hardware.py` | Serial LED/animation control | `HardwareInterface`, `ANIMATION_TOOLS`, `dispatch` |
| `main.py` | Wire everything, run the loop | (entry point) |

This unit (**Foundation & cleanup**) owns `config.py`, the package marker,
`config/config.example.yaml`, `requirements.txt`, and the test scaffolding.
The other modules are built by sibling agents against the contract above.

## Setup

```bash
# 1. Install dependencies (from the repo root)
pip install -r requirements.txt

# 2. Create the secrets file at the repo root (.env is gitignored)
#    OPENROUTER_API_KEY=sk-or-v1-...
#    ELEVENLABS_API_KEY=sk_...

# 3. Create your config from the example (config.yaml is gitignored)
cp wheatley_V2/config/config.example.yaml wheatley_V2/config/config.yaml

# 4. Run (once main.py lands)
python -m wheatley_V2.main
```

Secrets live **only** in `.env`. Everything else lives in `config.yaml`. The
example config never contains secrets.

## Switching LLM models

Model routing lives in the `llm` section of `config.yaml`:

```yaml
llm:
  default: deepseek/deepseek-chat-v3-0324   # the "intelligent" model
  fast: google/gemini-2.0-flash-001         # low time-to-first-token alternative
  max_tokens: 2000
  providers:
    deepseek/deepseek-chat-v3-0324: {sort: latency, order: [Together, Fireworks]}
```

- Change `default` to swap the main model. Any
  [OpenRouter model id](https://openrouter.ai/models) works.
- Use `fast` for latency-sensitive paths (it has a lower time-to-first-token).
- `providers` pins OpenRouter routing per model: `sort: latency` prefers the
  fastest backend; `order` sets a preferred provider list; `allow_fallbacks:
  false` keeps a request on the listed providers only.

## Latency design

The whole point of V2 is to shorten the gap between input and audible reply.

- **Streaming, not batching.** `openrouter.chat_stream` yields tokens as they
  arrive. `tts.TTSHandler` speaks each sentence the moment it is complete
  instead of waiting for the full reply. ElevenLabs `eleven_flash_v2_5` is the
  default TTS model for its low latency.
- **Overlap stages.** While the LLM is still generating sentence *n+1*, TTS is
  already speaking sentence *n*. STT, LLM, and TTS form a pipeline rather than
  three blocking steps.
- **No 3-second silence padding.** V1 appended ~3s of silence before sending
  audio to STT. V2 records to a short `silence_limit` (default 1.0s) and sends
  immediately.
- **No 500-chunk TTS buffering.** V1 buffered a large fixed number of audio
  chunks before playback. V2 plays audio as it streams in.
- **Fast model option.** Latency-sensitive turns can use `llm.fast` for a lower
  time-to-first-token, trading some quality for speed.
