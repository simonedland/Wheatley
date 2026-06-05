"""Stream text chunks to ElevenLabs TTS and play audio with low latency.

This module exposes :class:`TTSHandler`, a self-contained text-to-speech
streamer for Wheatley V2. It accumulates streamed text, splits it into
sentences, generates audio concurrently via the ElevenLabs API, and plays
the resulting audio in order. The design favours simplicity and low latency:
generation starts as soon as a complete sentence is available and playback
begins as soon as the first audio is ready, without large fixed buffers.

The module imports only the standard library and external dependencies; it
never imports sibling ``wheatley_V2`` modules (dependency injection).
"""

from __future__ import annotations

import asyncio
import io
import re
from typing import Any, Optional

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment  # type: ignore[import-not-found, import-untyped]
from pydub.playback import play  # type: ignore[import-not-found, import-untyped]

SENTENCE_END_RE = re.compile(r"[.!?]\s+")
ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st"}


class TTSHandler:
    """Stream text-to-speech using the ElevenLabs API.

    Manages sentence splitting, concurrent audio generation, and ordered
    playback. Generation and playback run as two background asyncio tasks
    started via :meth:`start`.
    """

    def __init__(
        self,
        api_key: str,
        voice_id: str = "4Jtuv4wBvd95o1hzNloV",
        model_id: str = "eleven_flash_v2_5",
    ) -> None:
        """Create a TTSHandler configured for the ElevenLabs API.

        Args:
            api_key: ElevenLabs API key used to create the client.
            voice_id: Identifier of the voice to use for synthesis.
            model_id: Identifier of the ElevenLabs model to use. Defaults to
                ``eleven_flash_v2_5`` for low-latency synthesis.
        """
        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id
        self.model_id = model_id

        # Optional ElevenLabs voice settings (None is acceptable).
        self.voice_settings: Optional[VoiceSettings] = None

        # Queues for passing data between workers.
        self.text_queue: asyncio.Queue[Optional[tuple[int, str]]] = asyncio.Queue()
        self.audio_queue: asyncio.Queue[tuple[int, Optional[bytes]]] = asyncio.Queue()

        # Buffer for accumulating text chunks until a full sentence is formed.
        self.text_buffer = ""
        self.scan_index = 0
        self.sent_count = 0

        # Tracking for active worker tasks.
        self.tasks: list[asyncio.Task[Any]] = []

        # Event set when the handler is idle; cleared when work is pending.
        self.idle_event = asyncio.Event()
        self.idle_event.set()

        # Counters for the idle check.
        self.pending_sent = 0
        self.pending_audio = 0

    @property
    def is_playing(self) -> bool:
        """Whether TTS generation or audio playback is currently active.

        Returns:
            ``True`` if processing or playback is active, ``False`` otherwise.
        """
        return not self.idle_event.is_set()

    def set_voice(self, voice_id: str, settings: dict | None = None) -> None:
        """Switch the voice and (optionally) voice settings at runtime.

        Useful for personality switches. When ``settings`` is provided, a
        :class:`elevenlabs.VoiceSettings` is built from the recognised keys
        (``stability``, ``similarity_boost``, ``style``, ``use_speaker_boost``,
        ``speed``); unrecognised keys are ignored. When ``settings`` is
        ``None`` the voice settings are left unchanged.

        Args:
            voice_id: Identifier of the voice to switch to.
            settings: Optional mapping of voice-setting overrides.
        """
        self.voice_id = voice_id
        if settings is not None:
            allowed = (
                "stability",
                "similarity_boost",
                "style",
                "use_speaker_boost",
                "speed",
            )
            kwargs = {k: settings[k] for k in allowed if k in settings}
            self.voice_settings = VoiceSettings(**kwargs)

    def _check_idle(self) -> None:
        """Set the idle event when no work is outstanding.

        Signals idle when there are no pending sentences, no pending audio,
        and both queues are empty.
        """
        if (
            self.pending_sent == 0
            and self.pending_audio == 0
            and self.text_queue.empty()
            and self.audio_queue.empty()
        ):
            self.idle_event.set()

    def start(self) -> None:
        """Start the background worker tasks for generation and playback."""
        self.tasks = [
            asyncio.create_task(self._proc_tts()),
            asyncio.create_task(self._play_audio()),
        ]

    async def flush_pending(self) -> None:
        """Flush any buffered partial sentence as a complete sentence."""
        if self.text_buffer.strip():
            self._push_sentence(self.text_buffer.strip())
            self.text_buffer = ""
            self.scan_index = 0

    def process_text(self, chunk: str) -> None:
        """Accumulate text chunks, split into sentences, and enqueue them.

        Sentences are split on :data:`SENTENCE_END_RE`. A guard avoids false
        splits after common abbreviations and after trailing digits (e.g.
        "3. " in an enumeration or a decimal number).

        Args:
            chunk: A streamed fragment of text to append to the buffer.
        """
        self.text_buffer += chunk
        while match := SENTENCE_END_RE.search(self.text_buffer, self.scan_index):
            end = match.end()
            # Guard against abbreviations or numbers to avoid false splits.
            pre = self.text_buffer[: match.start()].split()
            if pre and (pre[-1].lower() in ABBREVIATIONS or pre[-1].isdigit()):
                self.scan_index = end
                continue

            # Extract the sentence and advance the buffer.
            sent = self.text_buffer[:end].strip()
            self.text_buffer = self.text_buffer[end:].lstrip()
            self.scan_index = 0
            if sent:
                self._push_sentence(sent)

    def _push_sentence(self, sent: str) -> None:
        """Enqueue a complete sentence for TTS generation."""
        self.text_queue.put_nowait((self.sent_count, sent))
        self.sent_count += 1
        self.pending_sent += 1
        self.idle_event.clear()

    async def _proc_tts(self) -> None:
        """Fetch audio for queued sentences concurrently (semaphore-limited)."""
        sem = asyncio.Semaphore(2)
        tasks: list[asyncio.Task[Any]] = []

        async def _fetch(idx: int, txt: str) -> None:
            async with sem:
                # Run the blocking API call in the default executor.
                audio = await asyncio.get_running_loop().run_in_executor(
                    None, self._api_call, txt
                )
                if audio:
                    self.pending_audio += 1
                    self.idle_event.clear()
                await self.audio_queue.put((idx, audio))
                self.pending_sent -= 1
                self._check_idle()

        while True:
            item = await self.text_queue.get()
            if item is None:
                break
            tasks.append(asyncio.create_task(_fetch(*item)))

        if tasks:
            await asyncio.gather(*tasks)
        # Sentinel to tell the playback worker the stream has ended.
        await self.audio_queue.put((-1, b""))
        self._check_idle()

    async def _play_audio(self) -> None:
        """Play audio segments in sentence order, starting ASAP."""
        buf: dict[int, Optional[bytes]] = {}
        expect = 0
        stream_done = False
        started = False

        while True:
            idx, audio = await self.audio_queue.get()
            if idx == -1:
                stream_done = True
            else:
                buf[idx] = audio

            # Begin once the first (and ideally second) sentence is ready.
            if not started:
                have_first = expect in buf
                have_second = (expect + 1) in buf
                if not (have_first and (have_second or stream_done)):
                    continue
                started = True

            while expect in buf:
                if data := buf.pop(expect):
                    await asyncio.get_running_loop().run_in_executor(
                        None, self._play, data
                    )
                expect += 1
                if self.pending_audio > 0:
                    self.pending_audio -= 1
                self._check_idle()

            if stream_done and not buf:
                break
        self._check_idle()

    def _api_call(self, text: str) -> Optional[bytes]:
        """Call the ElevenLabs SDK and return MP3 audio bytes.

        Args:
            text: The sentence to synthesise.

        Returns:
            The MP3-encoded audio as ``bytes``, or ``None`` on error.
        """
        try:
            kwargs: dict[str, Any] = {
                "voice_id": self.voice_id,
                "model_id": self.model_id,
                "text": text,
                "output_format": "mp3_22050_32",
            }
            if self.voice_settings is not None:
                kwargs["voice_settings"] = self.voice_settings
            audio_generator = self.client.text_to_speech.convert(**kwargs)
            return b"".join(audio_generator)
        except Exception as e:  # noqa: BLE001 - surface error, keep stream alive
            print(f"[TTS Error] {e}")
            return None

    def _play(self, data: bytes) -> None:
        """Play MP3 audio bytes using pydub."""
        try:
            play(AudioSegment.from_file(io.BytesIO(data), format="mp3"))
        except Exception as e:  # noqa: BLE001 - never let playback crash the worker
            print(f"[Playback Error] {e}")

    async def wait_idle(self) -> None:
        """Wait until all generation and playback have finished."""
        await self.idle_event.wait()

    def cleanup(self) -> None:
        """Release TTS resources (no persistent resources to free)."""
        pass
