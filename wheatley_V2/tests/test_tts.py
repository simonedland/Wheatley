"""Tests for :mod:`wheatley_V2.tts`.

Unit tests run fully offline: the ElevenLabs client and pydub are stubbed so
no network access or audio device is required. A single live test is guarded
by the presence of the ``ELEVENLABS_API_KEY`` environment variable and only
asserts that real MP3 bytes are returned (no playback device needed).
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import sys
import types
from unittest.mock import MagicMock, patch

# Ensure the repository root (parents[2]) is importable so `wheatley_V2`
# resolves regardless of where pytest is invoked from.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# Load the repo-root .env (if present) so the live test can read the key.
try:
    from dotenv import load_dotenv

    load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")
except Exception:
    pass


def _stub_pydub() -> None:
    """Install minimal stubs for pydub so import + playback never touch audio."""
    if "pydub" not in sys.modules:
        pydub_module = types.ModuleType("pydub")
        pydub_module.__path__ = []  # mark as package

        class _DummyAudioSegment:
            @staticmethod
            def from_file(*args, **kwargs):
                return MagicMock()

        pydub_module.AudioSegment = _DummyAudioSegment
        sys.modules["pydub"] = pydub_module

    if "pydub.playback" not in sys.modules:
        playback_module = types.ModuleType("pydub.playback")
        playback_module.play = MagicMock()
        sys.modules["pydub.playback"] = playback_module


def _stub_elevenlabs() -> None:
    """Install minimal stubs for the elevenlabs package if it is unavailable.

    This lets the offline unit tests run without the real SDK installed. If the
    real package is importable it is left untouched (used by the live test).
    """
    try:
        import elevenlabs  # noqa: F401
        from elevenlabs import VoiceSettings  # noqa: F401
        from elevenlabs.client import ElevenLabs  # noqa: F401

        return
    except Exception:
        pass

    elevenlabs_module = types.ModuleType("elevenlabs")
    elevenlabs_module.__path__ = []

    class _VoiceSettings:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    elevenlabs_module.VoiceSettings = _VoiceSettings

    client_module = types.ModuleType("elevenlabs.client")

    class _ElevenLabs:
        def __init__(self, *args, **kwargs):
            self.text_to_speech = MagicMock()

    client_module.ElevenLabs = _ElevenLabs
    elevenlabs_module.client = client_module

    sys.modules["elevenlabs"] = elevenlabs_module
    sys.modules["elevenlabs.client"] = client_module


_stub_pydub()
_stub_elevenlabs()

import pytest  # noqa: E402

from wheatley_V2 import tts  # noqa: E402


def _make_handler() -> tts.TTSHandler:
    """Build a TTSHandler with the ElevenLabs client patched out."""
    with patch.object(tts, "ElevenLabs") as mock_eleven:
        mock_eleven.return_value.text_to_speech = MagicMock()
        return tts.TTSHandler("fake_key")


# ---------------------------------------------------------------------------
# Sentence splitting / enqueue behaviour (offline, no event loop needed)
# ---------------------------------------------------------------------------


def _queued_texts(handler: tts.TTSHandler) -> list[str]:
    """Drain the text queue and return the enqueued sentence strings."""
    out = []
    while not handler.text_queue.empty():
        item = handler.text_queue.get_nowait()
        if item is not None:
            out.append(item[1])
    return out


def test_splits_multiple_sentences():
    handler = _make_handler()
    # Trailing space ensures the final terminator is followed by whitespace
    # (the regex requires whitespace after . ! ?).
    handler.process_text("Hello world. This is a test! Is it working? ")
    texts = _queued_texts(handler)
    assert texts == ["Hello world.", "This is a test!", "Is it working?"]


def test_terminator_without_trailing_whitespace_stays_buffered():
    """A terminator with no following whitespace is not yet a complete split."""
    handler = _make_handler()
    handler.process_text("Hello world. Pending?")
    texts = _queued_texts(handler)
    assert texts == ["Hello world."]
    assert handler.text_buffer == "Pending?"


def test_streamed_chunks_accumulate():
    """Sentences may arrive split across multiple chunks."""
    handler = _make_handler()
    handler.process_text("Hello ")
    handler.process_text("world. Second ")
    handler.process_text("sentence here. ")
    texts = _queued_texts(handler)
    assert texts == ["Hello world.", "Second sentence here."]


def test_partial_sentence_not_enqueued_until_complete():
    handler = _make_handler()
    handler.process_text("This has no terminator yet")
    assert handler.text_queue.empty()
    # Completing the sentence (terminator + whitespace) enqueues it.
    handler.process_text(". Now buffered")
    texts = _queued_texts(handler)
    assert texts == ["This has no terminator yet."]
    assert handler.text_buffer == "Now buffered"


def test_abbreviations_do_not_split():
    handler = _make_handler()
    handler.process_text("Mr. Smith met Dr. Jones. They talked. ")
    texts = _queued_texts(handler)
    assert texts == ["Mr. Smith met Dr. Jones.", "They talked."]


def test_numbers_do_not_split():
    """A digit immediately before the period must not trigger a split."""
    handler = _make_handler()
    handler.process_text("The value is 3. 14 is close to pi. ")
    texts = _queued_texts(handler)
    # "3. " is guarded (trailing digit), so it does not split there.
    assert texts == ["The value is 3. 14 is close to pi."]


def test_count_matches_number_of_sentences():
    handler = _make_handler()
    handler.process_text("One. Two. Three. Four. ")
    texts = _queued_texts(handler)
    assert len(texts) == 4
    assert handler.sent_count == 4


# ---------------------------------------------------------------------------
# flush_pending
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flush_pending_emits_trailing_text():
    handler = _make_handler()
    handler.process_text("Complete one. Trailing without period")
    # One complete sentence so far.
    assert handler.text_queue.qsize() == 1
    await handler.flush_pending()
    texts = _queued_texts(handler)
    assert texts == ["Complete one.", "Trailing without period"]


@pytest.mark.asyncio
async def test_flush_pending_noop_when_empty():
    handler = _make_handler()
    handler.process_text("All done. ")
    before = handler.text_queue.qsize()
    await handler.flush_pending()
    assert handler.text_queue.qsize() == before


# ---------------------------------------------------------------------------
# set_voice
# ---------------------------------------------------------------------------


def test_set_voice_updates_id_only():
    handler = _make_handler()
    handler.set_voice("new_voice")
    assert handler.voice_id == "new_voice"
    assert handler.voice_settings is None


def test_set_voice_builds_voice_settings():
    handler = _make_handler()
    handler.set_voice(
        "v2",
        {
            "stability": 0.4,
            "similarity_boost": 0.2,
            "style": 0.1,
            "use_speaker_boost": True,
            "speed": 0.9,
            "ignored_key": 123,
        },
    )
    assert handler.voice_id == "v2"
    assert handler.voice_settings is not None
    # Recognised keys are applied; unknown keys ignored.
    assert getattr(handler.voice_settings, "stability") == 0.4
    assert getattr(handler.voice_settings, "speed") == 0.9
    assert not hasattr(handler.voice_settings, "ignored_key")


# ---------------------------------------------------------------------------
# _api_call (mocked client)
# ---------------------------------------------------------------------------


def test_api_call_returns_joined_bytes():
    handler = _make_handler()
    handler.client.text_to_speech.convert = MagicMock(
        return_value=iter([b"chunk1", b"chunk2"])
    )
    result = handler._api_call("Hello there.")
    assert result == b"chunk1chunk2"
    _, kwargs = handler.client.text_to_speech.convert.call_args
    assert kwargs["text"] == "Hello there."
    assert kwargs["voice_id"] == handler.voice_id
    assert kwargs["model_id"] == "eleven_flash_v2_5"
    assert kwargs["output_format"] == "mp3_22050_32"
    # No voice_settings sent when none configured.
    assert "voice_settings" not in kwargs


def test_api_call_includes_voice_settings_when_set():
    handler = _make_handler()
    handler.set_voice("v", {"stability": 0.5})
    handler.client.text_to_speech.convert = MagicMock(return_value=iter([b"x"]))
    handler._api_call("Hi.")
    _, kwargs = handler.client.text_to_speech.convert.call_args
    assert "voice_settings" in kwargs


def test_api_call_returns_none_on_error():
    handler = _make_handler()
    handler.client.text_to_speech.convert = MagicMock(side_effect=Exception("API down"))
    assert handler._api_call("Hi.") is None


def test_default_model_is_flash():
    handler = _make_handler()
    assert handler.model_id == "eleven_flash_v2_5"


# ---------------------------------------------------------------------------
# Full pipeline (mocked api + play)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_generates_and_plays_each_sentence():
    handler = _make_handler()
    with patch.object(
        handler, "_api_call", return_value=b"audio"
    ) as mock_api, patch.object(handler, "_play") as mock_play:
        handler.start()
        handler.process_text("Hello world. This is a test. ")
        await handler.flush_pending()
        await handler.text_queue.put(None)
        await asyncio.gather(*handler.tasks)

    assert mock_api.call_count == 2
    assert mock_play.call_count == 2


# ---------------------------------------------------------------------------
# Live test (guarded by ELEVENLABS_API_KEY)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("ELEVENLABS_API_KEY"),
    reason="ELEVENLABS_API_KEY not set; skipping live ElevenLabs test",
)
def test_live_api_call_returns_mp3_bytes():
    """Hit the real ElevenLabs API and assert non-empty MP3 bytes are returned.

    No audio device is required: only the bytes returned by ``_api_call`` are
    asserted; the ``_play`` speaker step is never invoked.
    """
    # Use the real elevenlabs SDK for this test (not the stub).
    if getattr(sys.modules.get("elevenlabs"), "__path__", None) == []:
        pytest.skip("real elevenlabs SDK not installed")

    api_key = os.environ["ELEVENLABS_API_KEY"]
    handler = tts.TTSHandler(api_key)
    audio = handler._api_call("Hello, this is a test of Wheatley.")
    assert isinstance(audio, bytes)
    assert len(audio) > 0
