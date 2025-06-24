# Service Authentication

## Purpose
Check external service credentials at startup and disable unavailable integrations.

## Usage
- When `main.py` runs, `authenticate_services()` attempts to log in to Google, Spotify, OpenAI and ElevenLabs.
- Each service is printed with a green check mark on success or a red cross on failure.
- Tools and features for failed services are automatically disabled.

## Internals
- `service_auth.authenticate_services` instantiates `GoogleAgent` and `SpotifyAgent`, and verifies OpenAI and ElevenLabs API keys.
- Authentication results are stored in `service_auth.SERVICE_STATUS`.
- `build_tools` removes Google or Spotify tools when authentication fails.
- `Functions` skips agent calls if the corresponding service is unavailable.

## Examples
```bash
$ python main.py
Authenticating external services:
✔ Google
✘ Spotify
✔ OpenAI
✘ ElevenLabs
```
