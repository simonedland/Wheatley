"""Settings loader for Wheatley V2.

Secrets live in the repo-root ``.env`` file (gitignored) and are loaded with
``python-dotenv``. Everything else lives in ``wheatley_V2/config/config.yaml``
(also gitignored). Copy ``config/config.example.yaml`` to ``config/config.yaml``
to get started.

Typical usage::

    from wheatley_V2.config import load_settings

    settings = load_settings()
    print(settings.llm["default"])
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Repo root is two levels up from this file: wheatley_V2/config.py -> repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ENV_PATH = _REPO_ROOT / ".env"
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "config.yaml"


@dataclass
class Settings:
    """All resolved configuration for a Wheatley V2 run.

    Secrets come from ``.env``; the rest comes from ``config.yaml``.

    Attributes:
        openrouter_api_key: API key for OpenRouter (STT + LLM).
        elevenlabs_api_key: API key for ElevenLabs (TTS).
        llm: LLM section (models, max_tokens, per-model provider routing).
        stt: Speech-to-text section (model, provider, audio params).
        tts: Text-to-speech section (voice/model ids, enabled flag).
        wake_word: Wake-word section (engine, model, threshold).
        personalities: Mapping of personality name -> personality config.
        current_personality: Name of the active personality (a key of
            ``personalities``).
        hardware: Optional serial hardware section (enabled, port, baud_rate).
    """

    openrouter_api_key: str
    elevenlabs_api_key: str
    llm: dict[str, Any]
    stt: dict[str, Any]
    tts: dict[str, Any]
    wake_word: dict[str, Any]
    personalities: dict[str, Any]
    current_personality: str
    hardware: dict[str, Any]


def get_secret(name: str) -> str | None:
    """Return a secret from the process environment (loaded from ``.env``).

    Loads the repo-root ``.env`` file on first call so callers can read secrets
    without constructing a full :class:`Settings`. Existing environment
    variables are never overwritten.

    Args:
        name: Environment variable name, e.g. ``"OPENROUTER_API_KEY"``.

    Returns:
        The secret value, or ``None`` if it is not set.
    """
    load_dotenv(_DEFAULT_ENV_PATH, override=False)
    return os.environ.get(name)


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping from ``path`` with clear errors.

    Args:
        path: Path to the YAML config file.

    Returns:
        The parsed mapping.

    Raises:
        FileNotFoundError: If ``path`` does not exist. The message points the
            user at ``config.example.yaml``.
        ValueError: If the file does not contain a YAML mapping.
    """
    if not path.exists():
        example = path.parent / "config.example.yaml"
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            f"Copy the example to get started:\n"
            f"    cp {example} {path}"
        )

    with path.open("r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)

    if not isinstance(loaded, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {path}")
    return loaded


def load_settings(path: str | os.PathLike[str] | None = None) -> Settings:
    """Load secrets from ``.env`` and config from ``config.yaml``.

    Args:
        path: Optional path to a YAML config file. Defaults to
            ``wheatley_V2/config/config.yaml``.

    Returns:
        A fully populated :class:`Settings`.

    Raises:
        FileNotFoundError: If the config file is missing.
        ValueError: If the config file is malformed.
        KeyError: If the active ``current_personality`` is not defined in
            ``personalities``.
    """
    load_dotenv(_DEFAULT_ENV_PATH, override=False)

    config_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    cfg = _load_yaml(config_path)

    current_personality = cfg.get("current_personality", "normal")
    personalities = cfg.get("personalities", {})
    if personalities and current_personality not in personalities:
        available = ", ".join(sorted(personalities)) or "(none)"
        raise KeyError(
            f"current_personality '{current_personality}' is not defined in "
            f"personalities. Available: {available}"
        )

    return Settings(
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
        llm=cfg.get("llm", {}),
        stt=cfg.get("stt", {}),
        tts=cfg.get("tts", {}),
        wake_word=cfg.get("wake_word", {}),
        personalities=personalities,
        current_personality=current_personality,
        hardware=cfg.get("hardware", {}),
    )
