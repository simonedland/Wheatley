# Personality Switcher

## Purpose
Provides a tool for the LLM to dynamically switch Wheatley's personality. Each personality defines a system message and text-to-speech (TTS) configuration.

## Usage
- Personalities are defined in `config.yaml` under the `personalities` section.
- The currently active personality is stored in `current_personality`.
- The LLM calls the `set_personality` tool with `mode` set to either `normal` or `western`.

## Internals
The tool updates `config.yaml` with the selected personality's `system_message` and TTS settings. The `TextToSpeechEngine` reloads its configuration before generating speech so changes take effect immediately.

## Examples
```python
from llm.llm_client import Functions
Functions().set_personality("western")
```
