"""Small helper to stream text chunks to ElevenLabs TTS and play audio."""

import asyncio
import importlib
import io
import re
from typing import TYPE_CHECKING, Any, Optional

import requests

if TYPE_CHECKING:
    # Minimal typing surface; runtime modules are loaded dynamically below.
    class AudioSegment:
        @staticmethod
        def from_file(file: Any, format: str): ...

    def play(segment: Any) -> None: ...

ENABLE_CONTEXT_AWARE_TTS = False

SENTENCE_END_RE = re.compile(r"[.!?]\s+")
ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st"}


class TTSHandler:
    """
    Stream text-to-speech using ElevenLabs API.

    Manages sentence splitting, concurrent audio generation, and sequential playback.
    """

    def __init__(
        self,
        xi_api_key: str,
        voice_id: str = "4Jtuv4wBvd95o1hzNloV",
        model_id: str = "eleven_flash_v2_5",
    ):
        """Initialize handler with API credentials and defaults."""
        self.api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        self.headers = {"xi-api-key": xi_api_key, "Content-Type": "application/json"}
        self.model_id = model_id
        # Queues for passing data between workers
        self.text_queue: asyncio.Queue[
            tuple[int, str, Optional[str], Optional[str]]
        ] = asyncio.Queue()
        self.audio_queue: asyncio.Queue[tuple[int, Optional[bytes]]] = asyncio.Queue()
        # Buffer for accumulating text chunks until a full sentence is formed
        self.text_buffer = ""
        self.scan_index = 0
        self.sent_count = 0
        # Tracking for active tasks and pending work items
        self.tasks: list[asyncio.Task[Any]] = []
        self.pending_sent = 0
        self.pending_audio = 0
        # Buffering for context-aware generation (previous/next text)
        self.last_text: Optional[str] = None
        self.buffered_item: Optional[tuple[int, str]] = None
        # Event to signal when all processing and playback is complete
        self.idle_event = asyncio.Event()
        self.idle_event.set()

    def _maybe_idle(self):
        """Check queues and counters then set the idle event when clear."""
        if not (
            self.pending_sent
            or self.pending_audio
            or not self.text_queue.empty()
            or not self.audio_queue.empty()
            or self.buffered_item
        ):
            self.idle_event.set()

    def start(self):
        """Start background worker tasks for TTS generation and playback."""
        self.tasks = [
            asyncio.create_task(self._proc_tts()),
            asyncio.create_task(self._play_audio()),
        ]

    async def flush_pending(self):
        """Force any remaining buffered text to be processed as a sentence."""
        if self.text_buffer.strip():
            self._push_sentence(self.text_buffer.strip())
            self.text_buffer = ""
            self.scan_index = 0

        if self.buffered_item:
            idx, txt = self.buffered_item
            self.text_queue.put_nowait((idx, txt, self.last_text, None))
            self.last_text = txt
            self.pending_sent += 1
            self.buffered_item = None
            self.idle_event.clear()

    def process_text(self, chunk: str):
        """Accumulate text chunks, split into sentences, and enqueue for processing."""
        self.text_buffer += chunk
        while match := SENTENCE_END_RE.search(self.text_buffer, self.scan_index):
            end = match.end()
            # Check for abbreviations or numbers to avoid false positives on sentence splitting
            pre = self.text_buffer[: match.start()].split()
            if pre and (pre[-1].lower() in ABBREVIATIONS or pre[-1].isdigit()):
                self.scan_index = end
                continue

            # Extract sentence and update buffer
            sent = self.text_buffer[:end].strip()
            self.text_buffer = self.text_buffer[end:].lstrip()
            self.scan_index = 0
            if sent:
                self._push_sentence(sent)

    def _push_sentence(self, sent: str):
        """Buffer sentence to determine next_text, then enqueue previous buffered sentence."""
        if not ENABLE_CONTEXT_AWARE_TTS:
            self.text_queue.put_nowait((self.sent_count, sent, None, None))
            self.sent_count += 1
            self.pending_sent += 1
            self.idle_event.clear()
            return

        if self.buffered_item:
            idx, txt = self.buffered_item
            self.text_queue.put_nowait((idx, txt, self.last_text, sent))
            self.last_text = txt
            self.pending_sent += 1

        self.buffered_item = (self.sent_count, sent)
        self.sent_count += 1
        self.idle_event.clear()

    async def _proc_tts(self):
        """Fetch audio for sentences concurrently (limited by semaphore)."""
        sem = asyncio.Semaphore(2)
        tasks = []

        async def _fetch(idx, txt, prev, nxt):
            async with sem:
                # Run blocking API call in executor
                audio = await asyncio.get_running_loop().run_in_executor(
                    None, self._api_call, txt, prev, nxt
                )
                if audio:
                    self.pending_audio += 1
                    self.idle_event.clear()
                await self.audio_queue.put((idx, audio))

        while (item := await self.text_queue.get()) is not None:
            if self.pending_sent:
                self.pending_sent -= 1
            tasks.append(asyncio.create_task(_fetch(*item)))

        if tasks:
            await asyncio.gather(*tasks)
        await self.audio_queue.put((-1, b""))
        self._maybe_idle()  # Signal playback worker to stop

    async def _play_audio(self):
        """Play audio segments in the correct order."""
        buf = {}
        expect = 0
        stream_done = False
        started = False

        while True:
            idx, audio = await self.audio_queue.get()
            if idx == -1:
                stream_done = True
            else:
                buf[idx] = audio

            # Wait until we have two sentences (or the stream ended early)
            if not started:
                have_first = expect in buf
                have_second = (expect + 1) in buf
                # Start only when first and second are ready, or if stream ended and only one exists
                if not (have_first and (have_second or stream_done)):
                    continue
                started = True

            while expect in buf:
                if data := buf.pop(expect):
                    await asyncio.get_running_loop().run_in_executor(
                        None, self._play, data
                    )
                expect += 1
                if self.pending_audio:
                    self.pending_audio -= 1
                    self._maybe_idle()

            if stream_done and not buf:
                break
        self._maybe_idle()

    def _api_call(self, text, prev=None, nxt=None):
        """Call ElevenLabs API and return audio bytes."""
        payload = {"text": text, "model_id": self.model_id}
        if prev:
            payload["previous_text"] = prev
        if nxt:
            payload["next_text"] = nxt

        try:
            r = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                params={"output_format": "mp3_22050_32"},
                timeout=60,
            )
            r.raise_for_status()
            return r.content
        except Exception as e:
            print(f"[TTS Error] {e}")
            if isinstance(e, requests.exceptions.HTTPError):
                print(f"[TTS Error Details] {r.text}")

    def _play(self, data):
        """Play audio bytes using pydub."""
        try:
            play(AudioSegment.from_file(io.BytesIO(data), format="mp3"))
        except Exception as e:
            print(f"[Playback Error] {e}")

    async def wait_idle(self):
        """Wait until all text is processed and audio playback finishes."""
        await self.idle_event.wait()
