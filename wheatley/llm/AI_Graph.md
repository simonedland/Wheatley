# AI Directory Structure

```mermaid
graph TD

%% File nodes
google_agent_py["google_agent.py"]
llm_client_py["llm_client.py"]
llm_client_utils_py["llm_client_utils.py"]
spotify_agent_py["spotify_agent.py"]
spotify_ha_utils_py["spotify_ha_utils.py"]

%% Relationships inferred from imports and usage

%% google_agent.py
google_agent_py --> llm_client_py %% (circular, but llm_client.py imports GoogleAgent)
google_agent_py --> llm_client_utils_py %% via openai, yaml, etc. (shared config, but not direct import)
google_agent_py --> spotify_agent_py %% via llm_client.py (indirect, see below)

%% llm_client.py
llm_client_py --> google_agent_py
llm_client_py --> spotify_agent_py
llm_client_py --> llm_client_utils_py
llm_client_py -->|record_timing, long_term_memory| utils_timing_logger["utils/timing_logger.py"]
llm_client_py -->|long_term_memory| utils_long_term_memory["utils/long_term_memory.py"]

%% llm_client_utils.py
llm_client_utils_py -->|SERVICE_STATUS| service_auth["service_auth.py"]

%% spotify_agent.py
spotify_agent_py --> spotify_ha_utils_py
spotify_agent_py --> google_agent_py %% via openai, yaml (shared config, not direct import)
spotify_agent_py -->|openai| llm_client_utils_py %% (shared config, not direct import)

%% spotify_ha_utils.py
spotify_ha_utils_py -->|spotipy| spotipy["spotipy (external)"]
spotify_ha_utils_py -->|yaml| yaml["yaml (external)"]
spotify_ha_utils_py -->|rich| rich["rich (optional, external)"]

%% External dependencies (not shown as nodes, but referenced in code)
google_agent_py -->|googleapiclient, google.oauth2| google_api["Google API (external)"]
llm_client_py -->|openai, elevenlabs, playsound, requests| openai["openai (external)"]
llm_client_py -->|elevenlabs| elevenlabs["elevenlabs (external)"]
llm_client_py -->|playsound| playsound["playsound (external)"]
llm_client_py -->|requests| requests["requests (external)"]
llm_client_utils_py -->|requests| requests

%% Service Auth
llm_client_utils_py --> service_auth
llm_client_py --> service_auth

%% Indirect/circular relationships
llm_client_py -.-> google_agent_py %% GoogleCalendarManager used in __main__

%% Tool/Agent relationships (usage)
llm_client_py -->|GoogleAgent, SpotifyAgent| google_agent_py
llm_client_py -->|SpotifyAgent| spotify_agent_py

%% Not shown: config.yaml, token.json, emotion_counter.json, etc. (external files)

%% Legend (not rendered in Mermaid, for reader reference)
%% - Solid arrows: direct imports or usage
%% - Dashed arrows: indirect usage or circular references
```
