"""Tests for wheatley_V2.openrouter.

Offline unit tests mock the OpenAI client and httpx. A guarded live test runs
only when ``OPENROUTER_API_KEY`` is set, hitting the real API.
"""

from __future__ import annotations

import pathlib
import sys
import wave
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from wheatley_V2.openrouter import (  # noqa: E402
    DEFAULT_STT_PROVIDER,
    MODEL_PRESETS,
    ChatChunk,
    OpenRouterClient,
)


# --------------------------------------------------------------------------- #
# Helpers for faking the OpenAI streaming objects.
# --------------------------------------------------------------------------- #
def _delta(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _chunk(content=None, tool_calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(delta=_delta(content, tool_calls))])


def _tc(index, *, id=None, name=None, arguments=None):
    func = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(index=index, id=id, function=func)


def _make_client(stream_chunks):
    """Build an OpenRouterClient whose OpenAI client returns ``stream_chunks``."""
    client = OpenRouterClient("sk-test", referer="http://x", title="T")

    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return iter(stream_chunks)

    client.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    return client, captured


# --------------------------------------------------------------------------- #
# Module-level constants
# --------------------------------------------------------------------------- #
def test_presets_and_provider_constants():
    assert MODEL_PRESETS["fast"] == "google/gemini-2.0-flash-001"
    assert MODEL_PRESETS["intelligent"] == "deepseek/deepseek-chat-v3-0324"
    assert MODEL_PRESETS["llama_groq"] == "meta-llama/llama-3.3-70b-instruct"
    assert DEFAULT_STT_PROVIDER == {"order": ["Groq"]}


# --------------------------------------------------------------------------- #
# chat_stream: text deltas
# --------------------------------------------------------------------------- #
def test_chat_stream_yields_text_deltas():
    chunks = [_chunk("Hello"), _chunk(", "), _chunk("world"), _chunk(None)]
    client, captured = _make_client(chunks)

    out = list(client.chat_stream([{"role": "user", "content": "hi"}], model="m"))

    text = "".join(c.text for c in out)
    assert text == "Hello, world"
    # No tool calls -> no trailing tool-call chunk.
    assert all(c.tool_calls is None for c in out)
    assert captured["stream"] is True
    assert captured["model"] == "m"


def test_chat_stream_passes_provider_and_tools():
    client, captured = _make_client([_chunk("x")])
    tools = [{"type": "function", "function": {"name": "f"}}]
    provider = {"order": ["Groq"], "sort": "latency"}

    list(
        client.chat_stream(
            [{"role": "user", "content": "hi"}],
            model="m",
            tools=tools,
            max_tokens=42,
            provider=provider,
        )
    )

    assert captured["tools"] == tools
    assert captured["max_tokens"] == 42
    assert captured["extra_body"] == {"provider": provider}


# --------------------------------------------------------------------------- #
# chat_stream: tool-call assembly
# --------------------------------------------------------------------------- #
def test_chat_stream_assembles_tool_calls():
    # Tool-call arguments arrive fragmented across multiple chunks.
    chunks = [
        _chunk(tool_calls=[_tc(0, id="call_1", name="get_weather", arguments='{"ci')]),
        _chunk(tool_calls=[_tc(0, arguments='ty": "Os')]),
        _chunk(tool_calls=[_tc(0, arguments='lo"}')]),
        _chunk("done"),
    ]
    client, _ = _make_client(chunks)

    out = list(client.chat_stream([{"role": "user", "content": "weather?"}], model="m"))

    final = out[-1]
    assert final.tool_calls is not None
    assert len(final.tool_calls) == 1
    call = final.tool_calls[0]
    assert call["id"] == "call_1"
    assert call["name"] == "get_weather"
    assert call["arguments"] == {"city": "Oslo"}


def test_chat_stream_assembles_multiple_tool_calls():
    chunks = [
        _chunk(tool_calls=[_tc(0, id="a", name="f0", arguments="{}")]),
        _chunk(tool_calls=[_tc(1, id="b", name="f1", arguments='{"x": 1}')]),
    ]
    client, _ = _make_client(chunks)

    out = list(client.chat_stream([{"role": "user", "content": "go"}], model="m"))
    calls = out[-1].tool_calls

    assert [c["id"] for c in calls] == ["a", "b"]
    assert calls[0]["arguments"] == {}
    assert calls[1]["arguments"] == {"x": 1}


# --------------------------------------------------------------------------- #
# transcribe
# --------------------------------------------------------------------------- #
def test_transcribe_builds_request_and_returns_text(monkeypatch):
    import wheatley_V2.openrouter as orm

    captured: dict = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"text": "hello there"}

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(orm.httpx, "post", fake_post)

    client = OpenRouterClient("sk-test")
    result = client.transcribe(b"RIFFfake", fmt="wav", language="en")

    assert result == "hello there"
    assert captured["url"].endswith("/audio/transcriptions")
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    body = captured["json"]
    assert body["model"] == "openai/whisper-large-v3-turbo"
    assert body["input_audio"]["format"] == "wav"
    assert body["language"] == "en"
    # Default provider routing applied.
    assert body["provider"] == DEFAULT_STT_PROVIDER
    # Audio is base64-encoded.
    import base64

    assert base64.b64decode(body["input_audio"]["data"]) == b"RIFFfake"


def test_transcribe_raises_on_non_200(monkeypatch):
    import wheatley_V2.openrouter as orm

    class FakeResponse:
        status_code = 401
        text = "unauthorized"

        def json(self):  # pragma: no cover - not reached
            return {}

    monkeypatch.setattr(orm.httpx, "post", lambda *a, **k: FakeResponse())

    client = OpenRouterClient("sk-test")
    with pytest.raises(RuntimeError) as exc:
        client.transcribe(b"x")
    assert "401" in str(exc.value)


def test_transcribe_custom_provider(monkeypatch):
    import wheatley_V2.openrouter as orm

    captured: dict = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"text": "ok"}

    def fake_post(url, *, headers, json, timeout):
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(orm.httpx, "post", fake_post)

    client = OpenRouterClient("sk-test")
    client.transcribe(b"x", provider={"order": ["Fireworks"]})
    assert captured["json"]["provider"] == {"order": ["Fireworks"]}


# --------------------------------------------------------------------------- #
# ChatChunk dataclass
# --------------------------------------------------------------------------- #
def test_chatchunk_defaults():
    c = ChatChunk()
    assert c.text == ""
    assert c.tool_calls is None


# --------------------------------------------------------------------------- #
# LIVE tests (skipped without an API key)
# --------------------------------------------------------------------------- #
def _api_key() -> str | None:
    import os

    from dotenv import load_dotenv

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")
    return os.getenv("OPENROUTER_API_KEY")


_LIVE_KEY = _api_key()
_live = pytest.mark.skipif(
    not _LIVE_KEY, reason="OPENROUTER_API_KEY not set; skipping live test"
)


def _make_silence_wav(seconds: float = 0.5, rate: int = 16000) -> bytes:
    """Synthesize a tiny mono 16-bit silent WAV in memory."""
    import io

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


@_live
def test_live_chat_stream():
    from openai import NotFoundError

    client = OpenRouterClient(_LIVE_KEY, title="Wheatley-Test")
    # Prefer the "fast" preset; fall back if the account lacks endpoints for it
    # (e.g. OpenRouter data-policy restrictions on a given provider).
    candidates = [MODEL_PRESETS["fast"], MODEL_PRESETS["intelligent"]]
    last_exc: Exception | None = None
    for model in candidates:
        try:
            text = "".join(
                c.text
                for c in client.chat_stream(
                    [{"role": "user", "content": "Say the single word: pong"}],
                    model=model,
                    max_tokens=20,
                )
            )
            assert text.strip() != ""
            return
        except NotFoundError as exc:  # no endpoints for this model on this account
            last_exc = exc
            continue
    pytest.skip(f"No usable chat model for this account: {last_exc}")


@_live
def test_live_transcribe():
    client = OpenRouterClient(_LIVE_KEY, title="Wheatley-Test")
    wav = _make_silence_wav()
    result = client.transcribe(wav, fmt="wav", language="en")
    assert isinstance(result, str)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
