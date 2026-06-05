"""Unit tests for ``wheatley_V2.stt`` (mic is always mocked)."""

from __future__ import annotations

import asyncio
import pathlib
import sys
import wave
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from wheatley_V2 import stt  # noqa: E402
from wheatley_V2.stt import VoiceListener  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------
def _pcm(amplitude: int, n: int = 1024) -> bytes:
    """Return ``n`` int16 samples all at ``amplitude`` as bytes."""
    return np.full(n, amplitude, dtype=np.int16).tobytes()


class FakeStream:
    """A fake PyAudio stream that yields a scripted sequence of frames."""

    def __init__(self, frames: list[bytes]):
        self._frames = list(frames)
        self.stopped = False
        self.closed = False

    def read(self, chunk, exception_on_overflow=False):
        if self._frames:
            return self._frames.pop(0)
        # After scripted frames are exhausted, emit silence forever.
        return _pcm(0, chunk)

    def stop_stream(self):
        self.stopped = True

    def close(self):
        self.closed = True


def make_fake_pyaudio(frames: list[bytes]):
    """Return a fake ``pyaudio`` module that produces ``FakeStream``."""
    fake_pa_instance = MagicMock()
    fake_pa_instance.open.return_value = FakeStream(frames)
    fake_pa_instance.get_sample_size.return_value = 2

    fake_pyaudio = MagicMock()
    fake_pyaudio.PyAudio.return_value = fake_pa_instance
    fake_pyaudio.paInt16 = 8
    return fake_pyaudio


def make_listener(transcribe_fn=lambda b: "hello", **wake_overrides):
    wake_cfg = {
        "enabled": False,
        "engine": "push_to_talk",
        "model": "hey_jarvis",
        "threshold": 0.5,
    }
    wake_cfg.update(wake_overrides)
    audio_cfg = {
        "rate": 16000,
        "threshold": 1000,
        "silence_limit": 0.1,  # short window -> fast tests
        "record_timeout": 0.5,  # bound the record loop so tests never hang
        "chunk": 1024,
        "channels": 1,
    }
    return VoiceListener(
        transcribe_fn,
        wake_cfg=wake_cfg,
        audio_cfg=audio_cfg,
        greeting_dir=None,
    )


# ---------------------------------------------------------------------------
# record_until_silent
# ---------------------------------------------------------------------------
def test_record_until_silent_returns_valid_wav():
    listener = make_listener()
    # One loud frame to trigger, then silence to end recording.
    loud = _pcm(5000)
    quiet = _pcm(0)
    frames = [loud] + [quiet] * 10

    with patch.object(stt, "pyaudio", make_fake_pyaudio(frames)):
        result = listener.record_until_silent()

    assert isinstance(result, bytes)
    # The bytes must parse as a valid WAV file.
    import io

    with wave.open(io.BytesIO(result), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        assert wf.getsampwidth() == 2
        assert wf.getnframes() > 0


def test_record_until_silent_timeout_returns_none():
    listener = make_listener()
    # Only quiet frames: never triggers sound -> times out -> None.
    frames = [_pcm(0)] * 5

    with patch.object(stt, "pyaudio", make_fake_pyaudio(frames)):
        result = listener.record_until_silent(max_wait_seconds=0.0)

    assert result is None


def test_record_until_silent_aborts_when_paused():
    listener = make_listener()
    listener.pause_listening()
    frames = [_pcm(5000)] * 5

    with patch.object(stt, "pyaudio", make_fake_pyaudio(frames)):
        result = listener.record_until_silent()

    assert result is None


# ---------------------------------------------------------------------------
# wait_for_wake
# ---------------------------------------------------------------------------
def test_wait_for_wake_push_to_talk(monkeypatch):
    listener = make_listener(engine="push_to_talk")
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")
    assert listener.wait_for_wake() is True


def test_wait_for_wake_ptt_eof_returns_false(monkeypatch):
    listener = make_listener(engine="push_to_talk")

    def _raise(*a, **k):
        raise EOFError

    monkeypatch.setattr("builtins.input", _raise)
    assert listener.wait_for_wake() is False


def test_wait_for_wake_openwakeword_detects():
    listener = make_listener(engine="openwakeword", threshold=0.5)

    # Fake oWW model that returns a high score immediately.
    fake_model = MagicMock()
    fake_model.predict.return_value = {"hey_jarvis": 0.99}
    # One frame so the loop reads once then matches.
    frames = [_pcm(100, 1280)]

    with patch.object(stt, "pyaudio", make_fake_pyaudio(frames)):
        with patch.object(listener, "_load_oww_model", return_value=fake_model):
            assert listener.wait_for_wake() is True
    fake_model.predict.assert_called()


def test_wait_for_wake_oww_falls_back_to_ptt(monkeypatch):
    listener = make_listener(engine="openwakeword")
    # Model load fails -> push-to-talk fallback.
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")
    with patch.object(listener, "_load_oww_model", return_value=None):
        assert listener.wait_for_wake() is True


# ---------------------------------------------------------------------------
# pause / resume
# ---------------------------------------------------------------------------
def test_pause_resume_state():
    listener = make_listener()
    assert listener.is_paused() is False
    listener.pause_listening()
    assert listener.is_paused() is True
    listener.resume_listening()
    assert listener.is_paused() is False


# ---------------------------------------------------------------------------
# greeting
# ---------------------------------------------------------------------------
def test_play_greeting_no_dir_is_noop():
    listener = make_listener()
    # No greeting_dir -> nothing happens, no error.
    listener.play_greeting(tts_engine=None)


def test_play_greeting_plays_mp3(tmp_path):
    mp3 = tmp_path / "hi.mp3"
    mp3.write_bytes(b"ID3fake")
    listener = make_listener()
    listener.greeting_dir = tmp_path

    engine = MagicMock()
    # Only expose play_mp3_bytes.
    engine.play_mp3_bytes = MagicMock()
    listener.play_greeting(tts_engine=engine)
    engine.play_mp3_bytes.assert_called_once_with(b"ID3fake")


def test_play_greeting_no_player_logs_only(tmp_path):
    (tmp_path / "hi.mp3").write_bytes(b"x")
    listener = make_listener()
    listener.greeting_dir = tmp_path
    # tts_engine without any play method -> just logs, no error.
    listener.play_greeting(tts_engine=object())


# ---------------------------------------------------------------------------
# hotword_listener end-to-end
# ---------------------------------------------------------------------------
async def test_hotword_listener_enqueues_transcription():
    listener = make_listener(transcribe_fn=lambda b: "hello")
    queue: asyncio.Queue = asyncio.Queue()

    loud = _pcm(5000)
    frames = [loud] + [_pcm(0)] * 10

    with patch.object(stt, "pyaudio", make_fake_pyaudio(frames)):
        # Force wake to trigger immediately, record real (mocked) audio.
        with patch.object(listener, "wait_for_wake", return_value=True):
            task = asyncio.create_task(listener.hotword_listener(queue))
            # Wait for one enqueued item.
            item = await asyncio.wait_for(queue.get(), timeout=2.0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    assert item == {"text": "hello", "source": "stt"}


async def test_hotword_listener_skips_empty_transcription():
    listener = make_listener(transcribe_fn=lambda b: "   ")
    queue: asyncio.Queue = asyncio.Queue()

    loud = _pcm(5000)
    frames = [loud] + [_pcm(0)] * 10

    with patch.object(stt, "pyaudio", make_fake_pyaudio(frames)):
        with patch.object(listener, "wait_for_wake", return_value=True):
            task = asyncio.create_task(listener.hotword_listener(queue))
            await asyncio.sleep(0.2)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    assert queue.empty()


async def test_hotword_listener_cancels_cleanly():
    listener = make_listener()
    listener.pause_listening()  # ensures loop just idles
    queue: asyncio.Queue = asyncio.Queue()

    task = asyncio.create_task(listener.hotword_listener(queue))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------
def test_cleanup_is_safe():
    listener = make_listener()
    listener._oww_model = MagicMock()
    listener.cleanup()
    assert listener._oww_model is None
    # Idempotent.
    listener.cleanup()
