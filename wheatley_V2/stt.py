"""Voice capture and wake-word detection for Wheatley V2.

This module is intentionally self-contained: it imports only the standard
library and external audio libraries. The transcription function is *injected*
as a callable so that this module never imports sibling ``wheatley_V2`` modules
(e.g. the OpenRouter client). This keeps the unit simple, fast and testable.

Wake word detection uses `openWakeWord <https://github.com/dscripka/openWakeWord>`_
(free, ONNX on Windows). Porcupine was dropped because it is now a paid service.
When wake word is disabled or openWakeWord is unavailable, a push-to-talk
(press Enter) fallback is used instead.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import random
import time
import wave
from pathlib import Path
from threading import Event
from typing import Callable

import numpy as np  # type: ignore[import-not-found]

# PyAudio is wrapped so this module imports even when the native library is
# unavailable (tests always mock it). Real recording requires it installed.
try:  # pragma: no cover - import guard
    import pyaudio  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - import guard
    pyaudio = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Default audio format used when PyAudio is available. 16-bit signed PCM.
_DEFAULT_FORMAT = pyaudio.paInt16 if pyaudio is not None else 8
# Number of bytes per sample for paInt16 (used when PyAudio is mocked).
_SAMPLE_WIDTH = 2

# openWakeWord native chunk size at 16kHz.
_OWW_CHUNK = 1280


class VoiceListener:
    """Capture microphone audio and detect a wake word.

    The listener exposes a two-phase silence-bounded recorder, a wake-word
    gate (openWakeWord or push-to-talk), and an async background loop that
    transcribes captured speech via an injected callable and enqueues results.

    Attributes:
        transcribe_fn: Callable taking WAV bytes and returning transcribed text.
        greeting_dir: Optional directory of ``.mp3`` greetings to play on wake.
    """

    def __init__(
        self,
        transcribe_fn: Callable[[bytes], str],
        *,
        wake_cfg: dict,
        audio_cfg: dict,
        greeting_dir: Path | None = None,
    ) -> None:
        """Initialize the listener.

        Args:
            transcribe_fn: Callable that takes WAV byte data and returns text.
                In production this is ``OpenRouterClient.transcribe``.
            wake_cfg: Wake word config with keys ``enabled`` (bool),
                ``engine`` (``"openwakeword"`` or ``"push_to_talk"``),
                ``model`` (str, e.g. ``"hey_jarvis"``) and ``threshold`` (float).
            audio_cfg: Audio config with keys ``rate``, ``threshold``,
                ``silence_limit`` and optional ``chunk`` and ``channels``.
            greeting_dir: Optional directory containing ``.mp3`` greeting files.
        """
        self.transcribe_fn = transcribe_fn

        self.wake_cfg = dict(wake_cfg)
        self.wake_enabled: bool = bool(self.wake_cfg.get("enabled", False))
        self.wake_engine: str = self.wake_cfg.get("engine", "push_to_talk")
        self.wake_model: str = self.wake_cfg.get("model", "hey_jarvis")
        self.wake_threshold: float = float(self.wake_cfg.get("threshold", 0.5))

        self.audio_cfg = dict(audio_cfg)
        self.RATE: int = int(self.audio_cfg.get("rate", 16000))
        self.THRESHOLD: int = int(self.audio_cfg.get("threshold", 1500))
        self.SILENCE_LIMIT: float = float(self.audio_cfg.get("silence_limit", 2))
        self.CHUNK: int = int(self.audio_cfg.get("chunk", 1024))
        self.CHANNELS: int = int(self.audio_cfg.get("channels", 1))
        self.FORMAT = _DEFAULT_FORMAT

        # Max seconds to wait for initial speech after a wake trigger before
        # giving up. Bounded so the background loop never blocks indefinitely.
        self.RECORD_TIMEOUT: float = float(self.audio_cfg.get("record_timeout", 8))

        self.greeting_dir = Path(greeting_dir) if greeting_dir is not None else None

        # Lazily created openWakeWord model (cached between wake cycles).
        self._oww_model = None

        self._pause_event = Event()

    # ------------------------------------------------------------------
    # Listening control
    # ------------------------------------------------------------------
    def pause_listening(self) -> None:
        """Pause the background listener loop."""
        if not self._pause_event.is_set():
            self._pause_event.set()
            logger.info("Listening paused.")

    def resume_listening(self) -> None:
        """Resume the background listener loop."""
        if self._pause_event.is_set():
            self._pause_event.clear()
            logger.info("Listening resumed.")

    def is_paused(self) -> bool:
        """Return whether listening is currently paused.

        Returns:
            True if paused, False otherwise.
        """
        return self._pause_event.is_set()

    # ------------------------------------------------------------------
    # TTS coordination helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _tts_playing(tts_engine) -> bool:
        """Return whether the given TTS engine is currently playing.

        Args:
            tts_engine: TTS engine instance or None.

        Returns:
            True if the engine exposes a truthy ``is_playing``.
        """
        return (
            tts_engine is not None
            and hasattr(tts_engine, "is_playing")
            and bool(tts_engine.is_playing)
        )

    def _should_abort(self, tts_engine) -> bool:
        """Return whether an in-progress recording should be aborted.

        Args:
            tts_engine: Optional TTS engine to check for active playback.

        Returns:
            True if paused or TTS is playing.
        """
        if self.is_paused():
            logger.debug("Recording aborted: paused.")
            return True
        if self._tts_playing(tts_engine):
            logger.debug("Recording aborted: TTS started.")
            return True
        return False

    # ------------------------------------------------------------------
    # Audio capture
    # ------------------------------------------------------------------
    def _open_stream(self, audio):
        """Open a PyAudio input stream for capture.

        Args:
            audio: A PyAudio instance.

        Returns:
            An open input stream.
        """
        return audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
        )

    @staticmethod
    def _amplitude(data: bytes) -> int:
        """Compute the peak absolute amplitude of a 16-bit PCM frame.

        Args:
            data: Raw 16-bit little-endian PCM bytes.

        Returns:
            Peak absolute amplitude (0 if the frame is empty).
        """
        samples = np.frombuffer(data, dtype=np.int16)
        if samples.size == 0:
            return 0
        return int(np.max(np.abs(samples)))

    def _monitor_for_sound(
        self, stream, start_time: float, max_wait_seconds: float | None, tts_engine
    ) -> list[bytes]:
        """Wait until audio above threshold is detected.

        Args:
            stream: Open PyAudio input stream.
            start_time: Monotonic start time used for the wait timeout.
            max_wait_seconds: Maximum seconds to wait for sound, or None.
            tts_engine: Optional TTS engine used to abort early.

        Returns:
            A list containing the first above-threshold frame, or empty list
            if aborted or timed out.
        """
        while True:
            if self._should_abort(tts_engine):
                return []
            if (
                max_wait_seconds is not None
                and time.time() - start_time > max_wait_seconds
            ):
                logger.debug("No sound detected before timeout.")
                return []
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            if self._amplitude(data) > self.THRESHOLD:
                logger.debug("Sound detected, recording...")
                return [data]

    def _continue_until_silence(
        self, stream, frames: list[bytes], tts_engine
    ) -> list[bytes]:
        """Keep recording until a sustained silence window is observed.

        Args:
            stream: Open PyAudio input stream.
            frames: Frames already captured (mutated in place).
            tts_engine: Optional TTS engine used to abort early.

        Returns:
            The collected frames, or an empty list if aborted.
        """
        silent_frames = 0
        # Number of consecutive silent chunks that constitute end-of-speech.
        silence_chunks = self.RATE / self.CHUNK * self.SILENCE_LIMIT
        while frames:
            if self._should_abort(tts_engine):
                return []
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            frames.append(data)
            if self._amplitude(data) > self.THRESHOLD:
                silent_frames = 0
            else:
                silent_frames += 1
            if silent_frames > silence_chunks:
                logger.debug("Silence detected, stopping.")
                break
        return frames

    def _frames_to_wav(self, frames: list[bytes], sample_width: int) -> bytes:
        """Encode raw PCM frames into in-memory WAV bytes.

        Args:
            frames: List of raw PCM byte frames.
            sample_width: Bytes per sample.

        Returns:
            Complete WAV file as a byte string.
        """
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(sample_width)
            wf.setframerate(self.RATE)
            wf.writeframes(b"".join(frames))
        return buffer.getvalue()

    def record_until_silent(
        self, max_wait_seconds: float | None = None, tts_engine=None
    ) -> bytes | None:
        """Record speech until a silence window and return WAV bytes.

        Two-phase capture: wait for sound above threshold, then continue
        recording until ``silence_limit`` seconds of silence. The audio is
        encoded to an in-memory WAV (no temp file).

        Args:
            max_wait_seconds: Maximum seconds to wait for initial sound, or None.
            tts_engine: Optional TTS engine; recording aborts if it starts.

        Returns:
            Complete WAV byte string, or None if nothing was recorded.
        """
        if pyaudio is None:  # pragma: no cover - exercised via mocks in tests
            raise RuntimeError("PyAudio is not available; cannot record audio.")

        start_time = time.time()
        audio = pyaudio.PyAudio()
        try:
            stream = self._open_stream(audio)
            try:
                frames = self._monitor_for_sound(
                    stream, start_time, max_wait_seconds, tts_engine
                )
                if frames:
                    frames = self._continue_until_silence(stream, frames, tts_engine)
            finally:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception as exc:  # pragma: no cover - cleanup best effort
                    logger.debug("Failed to close stream: %s", exc)

            if not frames:
                return None

            try:
                sample_width = audio.get_sample_size(self.FORMAT)
            except Exception:  # pragma: no cover - fallback when mocked
                sample_width = _SAMPLE_WIDTH
            return self._frames_to_wav(frames, sample_width)
        finally:
            try:
                audio.terminate()
            except Exception as exc:  # pragma: no cover - cleanup best effort
                logger.debug("Failed to terminate PyAudio: %s", exc)

    # ------------------------------------------------------------------
    # Wake word
    # ------------------------------------------------------------------
    def _load_oww_model(self):
        """Load (and cache) the openWakeWord model.

        Returns:
            The loaded openWakeWord ``Model`` instance, or None if the package
            is unavailable or loading failed.
        """
        if self._oww_model is not None:
            return self._oww_model
        try:
            from openwakeword.model import Model  # type: ignore[import-not-found]
        except Exception as exc:
            logger.warning("openWakeWord unavailable (%s); falling back.", exc)
            return None
        try:
            self._oww_model = Model(
                wakeword_models=[self.wake_model],
                inference_framework="onnx",
            )
        except Exception as exc:
            logger.warning("Failed to load openWakeWord model: %s", exc)
            return None
        return self._oww_model

    def _wait_for_wake_oww(self, tts_engine) -> bool:
        """Run an openWakeWord detection loop until the wake word fires.

        Args:
            tts_engine: Optional TTS engine; the loop pauses while it plays.

        Returns:
            True when the wake word is detected; False if it fell back or aborted.
        """
        model = self._load_oww_model()
        if model is None:
            return self._wait_for_wake_ptt()
        if pyaudio is None:  # pragma: no cover - guarded
            return self._wait_for_wake_ptt()

        audio = pyaudio.PyAudio()
        try:
            stream = audio.open(
                format=self.FORMAT,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=_OWW_CHUNK,
            )
            logger.info("Listening for wake word '%s'...", self.wake_model)
            try:
                while True:
                    if self.is_paused() or self._tts_playing(tts_engine):
                        time.sleep(0.1)
                        continue
                    data = stream.read(_OWW_CHUNK, exception_on_overflow=False)
                    samples = np.frombuffer(data, dtype=np.int16)
                    scores = model.predict(samples)
                    if any(score > self.wake_threshold for score in scores.values()):
                        logger.info("Wake word detected.")
                        return True
            finally:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception as exc:  # pragma: no cover - cleanup best effort
                    logger.debug("Failed to close wake stream: %s", exc)
        finally:
            try:
                audio.terminate()
            except Exception as exc:  # pragma: no cover - cleanup best effort
                logger.debug("Failed to terminate PyAudio: %s", exc)

    def _wait_for_wake_ptt(self) -> bool:
        """Block on push-to-talk (press Enter).

        Returns:
            True once the user presses Enter.
        """
        logger.info("Push-to-talk: press Enter to speak.")
        try:
            input()
        except EOFError:
            return False
        return True

    def wait_for_wake(self, tts_engine=None) -> bool:
        """Block until the wake gate triggers.

        Uses openWakeWord when ``engine == "openwakeword"`` and the package is
        available; otherwise falls back to push-to-talk (press Enter).

        Args:
            tts_engine: Optional TTS engine; openWakeWord pauses while it plays.

        Returns:
            True when triggered.
        """
        if self.wake_engine == "openwakeword":
            return self._wait_for_wake_oww(tts_engine)
        return self._wait_for_wake_ptt()

    # ------------------------------------------------------------------
    # Greeting
    # ------------------------------------------------------------------
    def play_greeting(self, tts_engine=None) -> None:
        """Play a random greeting MP3 from ``greeting_dir`` if possible.

        Non-fatal: if there is no directory, no MP3s, or no usable TTS engine,
        the greeting is skipped (and logged). When a TTS engine with a play
        method is provided the chosen file's bytes are handed to it.

        Args:
            tts_engine: Optional TTS engine used to play the greeting.
        """
        if self.greeting_dir is None:
            return
        try:
            if not self.greeting_dir.exists():
                return
            files = [
                f for f in os.listdir(self.greeting_dir) if f.lower().endswith(".mp3")
            ]
        except (FileNotFoundError, OSError):
            return
        if not files:
            return
        choice = random.choice(files)
        path = self.greeting_dir / choice

        play = None
        if tts_engine is not None:
            for name in ("play_mp3_bytes", "play_mp3", "play"):
                candidate = getattr(tts_engine, name, None)
                if callable(candidate):
                    play = candidate
                    break

        if play is None:
            logger.info("Greeting selected (no player available): %s", choice)
            return

        try:
            with open(path, "rb") as fh:
                play(fh.read())
            logger.debug("Played greeting: %s", choice)
        except Exception as exc:
            logger.warning("Failed to play greeting '%s': %s", choice, exc)

    # ------------------------------------------------------------------
    # Async background listener
    # ------------------------------------------------------------------
    async def hotword_listener(self, queue: asyncio.Queue, tts_engine=None) -> None:
        """Run the background wake-word + capture + transcribe loop.

        Each iteration waits for the wake gate, records until silence, then
        transcribes via the injected ``transcribe_fn``. Non-empty results are
        enqueued as ``{"text": ..., "source": "stt"}``. The loop skips work
        while paused or while TTS is playing, and exits cleanly on cancellation.

        Args:
            queue: Asyncio queue receiving transcription dicts.
            tts_engine: Optional TTS engine used to gate recording and play
                greetings.
        """
        logger.info("Background hotword listener started.")
        loop = asyncio.get_event_loop()
        try:
            while True:
                if self.is_paused() or self._tts_playing(tts_engine):
                    await asyncio.sleep(0.1)
                    continue

                triggered = await loop.run_in_executor(
                    None, self.wait_for_wake, tts_engine
                )
                if not triggered or self.is_paused():
                    continue

                self.play_greeting(tts_engine)

                wav_bytes = await loop.run_in_executor(
                    None, self.record_until_silent, self.RECORD_TIMEOUT, tts_engine
                )
                if not wav_bytes or self.is_paused():
                    continue

                text = await loop.run_in_executor(None, self.transcribe_fn, wav_bytes)
                if text and text.strip():
                    logger.info("Transcribed: %s", text.strip())
                    await queue.put({"text": text.strip(), "source": "stt"})
        except asyncio.CancelledError:
            logger.info("Hotword listener cancelled.")
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Hotword listener error: %s", exc)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def cleanup(self) -> None:
        """Release wake-word resources. Safe to call multiple times."""
        if self._oww_model is not None:
            self._oww_model = None
        logger.debug("VoiceListener cleaned up.")
