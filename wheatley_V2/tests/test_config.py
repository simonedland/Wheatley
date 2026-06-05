"""Tests for :mod:`wheatley_V2.config`."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from wheatley_V2 import config as config_module
from wheatley_V2.config import Settings, get_secret, load_settings

_EXAMPLE_YAML = textwrap.dedent(
    """
    llm:
      default: deepseek/deepseek-chat-v3-0324
      fast: google/gemini-2.0-flash-001
      max_tokens: 2000
      providers:
        deepseek/deepseek-chat-v3-0324: {sort: latency, order: [Together, Fireworks]}
    stt:
      model: openai/whisper-large-v3-turbo
      provider: {order: [Groq]}
      language: en
      rate: 16000
      silence_limit: 1.0
      threshold: 1500
    tts:
      enabled: true
      voice_id: 4Jtuv4wBvd95o1hzNloV
      model_id: eleven_flash_v2_5
    wake_word:
      enabled: true
      engine: openwakeword
      model: hey_jarvis
      threshold: 0.5
    current_personality: normal
    personalities:
      normal:
        system_message: "Test message"
        tts: {voice_id: 4Jtuv4wBvd95o1hzNloV, stability: 0.5}
    hardware:
      enabled: false
      port: COM3
      baud_rate: 115200
    """
)


@pytest.fixture()
def yaml_file(tmp_path: Path) -> Path:
    """Write the example config to a temp file and return its path."""
    path = tmp_path / "config.yaml"
    path.write_text(_EXAMPLE_YAML, encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop the real .env from being loaded and clear relevant env vars."""
    monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **k: False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)


def test_load_settings_returns_settings(yaml_file: Path) -> None:
    """A well-formed config produces a fully populated Settings object."""
    settings = load_settings(yaml_file)

    assert isinstance(settings, Settings)
    assert settings.llm["default"] == "deepseek/deepseek-chat-v3-0324"
    assert settings.llm["max_tokens"] == 2000
    assert settings.stt["model"] == "openai/whisper-large-v3-turbo"
    assert settings.tts["enabled"] is True
    assert settings.wake_word["engine"] == "openwakeword"
    assert settings.current_personality == "normal"
    assert "normal" in settings.personalities
    assert settings.hardware["enabled"] is False


def test_load_settings_reads_secrets_from_env(
    yaml_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Secrets are pulled from the environment, not the YAML file."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-eleven-test")

    settings = load_settings(yaml_file)

    assert settings.openrouter_api_key == "sk-or-test"
    assert settings.elevenlabs_api_key == "sk-eleven-test"


def test_load_settings_missing_secrets_default_to_empty(yaml_file: Path) -> None:
    """Missing secrets resolve to empty strings rather than raising."""
    settings = load_settings(yaml_file)

    assert settings.openrouter_api_key == ""
    assert settings.elevenlabs_api_key == ""


def test_load_settings_missing_file_raises(tmp_path: Path) -> None:
    """A missing config file raises a clear FileNotFoundError."""
    missing = tmp_path / "does_not_exist.yaml"

    with pytest.raises(FileNotFoundError) as exc:
        load_settings(missing)

    assert "Config file not found" in str(exc.value)


def test_load_settings_non_mapping_raises(tmp_path: Path) -> None:
    """A YAML file that is not a mapping raises ValueError."""
    path = tmp_path / "config.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_settings(path)


def test_load_settings_unknown_personality_raises(tmp_path: Path) -> None:
    """current_personality must exist in personalities."""
    path = tmp_path / "config.yaml"
    path.write_text(
        textwrap.dedent(
            """
            current_personality: ghost
            personalities:
              normal:
                system_message: "hi"
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(KeyError) as exc:
        load_settings(path)

    assert "ghost" in str(exc.value)


def test_get_secret_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_secret returns environment values and None when unset."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-xyz")

    assert get_secret("OPENROUTER_API_KEY") == "sk-or-xyz"
    assert get_secret("DEFINITELY_NOT_SET_12345") is None
