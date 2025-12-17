"""Helper functions for the main entrypoint."""

from typing import Tuple


def feature_summary(
    stt_enabled: bool, tts_enabled: bool, header: str = "Feature Status"
) -> str:
    """Return a formatted feature summary string."""
    summary = f"\n{header}:\n"
    summary += f" - Speech-to-Text (STT): {'Active' if stt_enabled else 'Inactive'}\n"
    summary += f" - Text-to-Speech (TTS): {'Active' if tts_enabled else 'Inactive'}\n"
    return summary


def authenticate_and_update_features(
    stt_enabled: bool, tts_enabled: bool
) -> Tuple[bool, bool]:
    """Authenticate external services and update feature flags accordingly."""
    from service_auth import authenticate_services  # type: ignore[import-not-found]

    service_status = authenticate_services()
    if not service_status.get("openai"):
        stt_enabled = False
    if not service_status.get("elevenlabs"):
        tts_enabled = False
    return stt_enabled, tts_enabled
