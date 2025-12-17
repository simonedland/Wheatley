"""Service authentication helpers for Wheatley."""

from __future__ import annotations

from typing import Dict
import os
import yaml

try:
    import openai  # type: ignore[import-not-found]
except Exception:  # openai may not be installed during documentation builds
    openai = None

try:
    from elevenlabs.client import ElevenLabs  # type: ignore[import-not-found]
except Exception:  # elevenlabs is optional
    ElevenLabs = None

from colorama import Fore, Style  # type: ignore[import-untyped]

try:
    from .llm.google_agent import GoogleAgent
    from .llm.spotify_agent import SpotifyAgent
except ImportError:  # fallback for running without package context
    from llm.google_agent import GoogleAgent  # type: ignore[import-not-found, no-redef]
    from llm.spotify_agent import SpotifyAgent  # type: ignore[import-not-found, no-redef]

SERVICE_STATUS: Dict[str, bool] = {}
GOOGLE_AGENT: GoogleAgent | None = None
SPOTIFY_AGENT: SpotifyAgent | None = None


def _load_config() -> Dict[str, Dict[str, str]]:
    """Return YAML configuration dictionary."""
    base_dir = os.path.dirname(__file__)
    config_path = os.path.join(base_dir, "config", "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _check_openai(api_key: str) -> bool:
    """Return ``True`` if ``api_key`` successfully authenticates with OpenAI."""
    if not openai or not api_key:
        return False
    try:
        if hasattr(openai, "OpenAI"):
            client = openai.OpenAI(api_key=api_key)
            client.models.list()
        else:  # older openai library
            openai.api_key = api_key
            openai.Model.list()
        return True
    except Exception:
        return False


def _check_elevenlabs(api_key: str) -> bool:
    """Return ``True`` if ``api_key`` is valid for ElevenLabs."""
    if not ElevenLabs or not api_key:
        return False
    try:
        client = ElevenLabs(api_key=api_key)
        # simple request to verify credentials
        client.voices.get_all()
        return True
    except Exception:
        return False


def authenticate_services() -> Dict[str, bool]:
    """Attempt to authenticate with all external services and print results."""
    global GOOGLE_AGENT, SPOTIFY_AGENT
    statuses: Dict[str, bool] = {}
    config = _load_config()
    print("\nAuthenticating external services:")

    # Google authentication (optional)
    if os.environ.get("WHEATLEY_DISABLE_GOOGLE", "0") not in {"1", "true", "TRUE"}:
        try:
            GOOGLE_AGENT = GoogleAgent()
            # Verify by listing calendars
            GOOGLE_AGENT.calendar_manager.list_calendars()
            print(Fore.GREEN + "✔ Google" + Style.RESET_ALL)
            statuses["google"] = True
        except KeyboardInterrupt:
            print(Fore.YELLOW + "⚠ Google auth cancelled by user" + Style.RESET_ALL)
            statuses["google"] = False
            GOOGLE_AGENT = None
        except Exception:
            print(Fore.RED + "✘ Google" + Style.RESET_ALL)
            statuses["google"] = False
            GOOGLE_AGENT = None
    else:
        print(
            Fore.YELLOW
            + "↷ Google auth skipped (WHEATLEY_DISABLE_GOOGLE set)"
            + Style.RESET_ALL
        )
        statuses["google"] = False

    # Spotify authentication
    try:
        SPOTIFY_AGENT = SpotifyAgent()
        SPOTIFY_AGENT.spotify.get_current_playback()
        print(Fore.GREEN + "✔ Spotify" + Style.RESET_ALL)
        statuses["spotify"] = True
    except Exception:
        print(Fore.RED + "✘ Spotify" + Style.RESET_ALL)
        statuses["spotify"] = False
        SPOTIFY_AGENT = None

    # OpenAI authentication
    if _check_openai(config["secrets"].get("openai_api_key", "")):
        print(Fore.GREEN + "✔ OpenAI" + Style.RESET_ALL)
        statuses["openai"] = True
    else:
        print(Fore.RED + "✘ OpenAI" + Style.RESET_ALL)
        statuses["openai"] = False

    # ElevenLabs authentication
    if _check_elevenlabs(config["secrets"].get("elevenlabs_api_key", "")):
        print(Fore.GREEN + "✔ ElevenLabs" + Style.RESET_ALL)
        statuses["elevenlabs"] = True
    else:
        print(Fore.RED + "✘ ElevenLabs" + Style.RESET_ALL)
        statuses["elevenlabs"] = False

    SERVICE_STATUS.update(statuses)
    return statuses
