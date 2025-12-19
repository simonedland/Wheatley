"""Small helper to stream text chunks to ElevenLabs TTS and play audio."""

import asyncio
import io
import re
from typing import Any, Optional

from elevenlabs.client import ElevenLabs
from pydub import AudioSegment  # type: ignore[import-not-found]
from pydub.playback import play  # type: ignore[import-not-found]

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
        """
        Create a TTSHandler configured to use the ElevenLabs API and initialize internal queues, buffers, and synchronization primitives.
        
        Parameters:
            xi_api_key (str): ElevenLabs API key used to create the client.
            voice_id (str): Identifier of the voice to use for synthesis (default provided).
            model_id (str): Identifier of the ElevenLabs model to use for synthesis (default provided).
        
        Attributes initialized:
            client: ElevenLabs client instance authenticated with xi_api_key.
            voice_id, model_id: Stored identifiers for voice and model selection.
            text_queue (asyncio.Queue[tuple[int, str]]): Queue of (sentence_index, sentence_text) for TTS generation.
            audio_queue (asyncio.Queue[tuple[int, Optional[bytes]]]): Queue of (sentence_index, audio_bytes) for ordered playback.
            text_buffer (str), scan_index (int), sent_count (int): Buffers and counters for sentence accumulation and indexing.
            tasks (list[asyncio.Task]): Background worker tasks tracking.
            idle_event (asyncio.Event): Event set when handler is idle; cleared when work is pending.
            pending_sent (int), pending_audio (int): Counters used to determine idle state.
        """
        self.client = ElevenLabs(api_key=xi_api_key)
        self.voice_id = voice_id
        self.model_id = model_id

        # Queues for passing data between workers
        self.text_queue: asyncio.Queue[tuple[int, str]] = asyncio.Queue()
        self.audio_queue: asyncio.Queue[tuple[int, Optional[bytes]]] = asyncio.Queue()

        # Buffer for accumulating text chunks until a full sentence is formed
        self.text_buffer = ""
        self.scan_index = 0
        self.sent_count = 0

        # Tracking for active tasks
        self.tasks: list[asyncio.Task[Any]] = []

        # Event to signal when all processing and playback is complete
        self.idle_event = asyncio.Event()
        self.idle_event.set()

        # Counters for idle check
        self.pending_sent = 0
        self.pending_audio = 0

    @property
    def is_playing(self) -> bool:
        """
        Indicates whether TTS processing or audio playback is active.
        
        Returns:
            `true` if TTS processing or playback is active, `false` otherwise.
        """
        return not self.idle_event.is_set()

    def _check_idle(self):
        """
        Set the idle event when there are no pending sentences, no pending audio, and both queues are empty.
        
        Checks self.pending_sent, self.pending_audio, self.text_queue, and self.audio_queue; if all indicate no outstanding work, signals idle by calling self.idle_event.set().
        """
        if (
            self.pending_sent == 0
            and self.pending_audio == 0
            and self.text_queue.empty()
            and self.audio_queue.empty()
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
        """Enqueue sentence for TTS generation."""
        self.text_queue.put_nowait((self.sent_count, sent))
        self.sent_count += 1
        self.pending_sent += 1
        self.idle_event.clear()

    async def _proc_tts(self):
        """Fetch audio for sentences concurrently (limited by semaphore)."""
        sem = asyncio.Semaphore(2)
        tasks = []

        async def _fetch(idx, txt):
            async with sem:
                # Run blocking API call in executor
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
        await self.audio_queue.put((-1, b""))
        self._check_idle()

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
                if self.pending_audio > 0:
                    self.pending_audio -= 1
                self._check_idle()

            if stream_done and not buf:
                break
        self._check_idle()

    def _api_call(self, text):
        """Call ElevenLabs SDK and return audio bytes."""
        try:
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                model_id=self.model_id,
                text=text,
                output_format="mp3_22050_32",
            )
            return b"".join(audio_generator)
        except Exception as e:
            print(f"[TTS Error] {e}")
            return None

    def _play(self, data):
        """Play audio bytes using pydub."""
        try:
            play(AudioSegment.from_file(io.BytesIO(data), format="mp3"))
        except Exception as e:
            print(f"[Playback Error] {e}")

    async def wait_idle(self):
        """Wait until all text is processed and audio playback finishes."""
        await self.idle_event.wait()