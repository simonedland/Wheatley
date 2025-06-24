"""Service authentication helpers for Wheatley."""

from __future__ import annotations

from typing import Dict

from colorama import Fore, Style

try:
    from .llm.google_agent import GoogleAgent
    from .llm.spotify_agent import SpotifyAgent
except ImportError:  # fallback for running without package context
    from llm.google_agent import GoogleAgent
    from llm.spotify_agent import SpotifyAgent

SERVICE_STATUS: Dict[str, bool] = {}
GOOGLE_AGENT: GoogleAgent | None = None
SPOTIFY_AGENT: SpotifyAgent | None = None


def authenticate_services() -> Dict[str, bool]:
    """Attempt to authenticate with external services.

    Returns:
        Mapping of service names to authentication success.
    """
    global GOOGLE_AGENT, SPOTIFY_AGENT
    statuses: Dict[str, bool] = {}
    print("\nAuthenticating external services:")

    # Google authentication
    try:
        GOOGLE_AGENT = GoogleAgent()
        print(Fore.GREEN + "✔ Google" + Style.RESET_ALL)
        statuses["google"] = True
    except (RuntimeError, ValueError):  # Replace with specific exceptions raised by GoogleAgent
        print(Fore.RED + "✘ Google" + Style.RESET_ALL)
        statuses["google"] = False
        GOOGLE_AGENT = None

    # Spotify authentication
    try:
        SPOTIFY_AGENT = SpotifyAgent()
        print(Fore.GREEN + "✔ Spotify" + Style.RESET_ALL)
        statuses["spotify"] = True
    except Exception:
        print(Fore.RED + "✘ Spotify" + Style.RESET_ALL)
        statuses["spotify"] = False
        SPOTIFY_AGENT = None

    SERVICE_STATUS.update(statuses)
    return statuses
