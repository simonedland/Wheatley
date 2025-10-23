"""
Simple wrapper around the ElevenLabs TTS API.

This module exposes :class:`TextToSpeechEngine` which converts text to
speech using the ElevenLabs API and plays the result back. The class is
configured via `config/config.yaml` and keeps the interface minimal so
that it can be reused throughout the project.
"""

from __future__ import annotations
import logging
import os
import time
import io
import yaml

from utils.timing_logger import record_timing
import pyaudio
from pydub import AudioSegment
from pydub.generators import Sine
import threading
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings


class TextToSpeechEngine:
    """Interface to ElevenLabs TTS with persistent playback stream."""

    def is_playing(self) -> bool:
        """Return True if TTS is currently playing audio."""
        return self._playing.is_set()

    def _load_config(self) -> None:
        """Load voice settings from configuration file."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "config.yaml",
        )
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        tts_config = config.get("tts", {})
        self.api_key = config["secrets"]["elevenlabs_api_key"]
        self.voice_id = tts_config.get("voice_id", "4Jtuv4wBvd95o1hzNloV")
        self.voice_settings = VoiceSettings(
            stability=tts_config.get("stability", 0.3),
            similarity_boost=tts_config.get("similarity_boost", 0.1),
            style=tts_config.get("style", 0.0),
            use_speaker_boost=tts_config.get("use_speaker_boost", True),
            speed=tts_config.get("speed", 0.8),
        )
        self.model_id = tts_config.get("model_id", "eleven_flash_v2_5")
        self.output_format = tts_config.get("output_format", "mp3_22050_32")

    def __init__(self):
        """Initialise the TTS engine and load configuration."""
        self._load_config()

        # Silence noisy logging from the ElevenLabs library
        logging.getLogger("elevenlabs").setLevel(logging.WARNING)

        # Reuse one API client for all requests
        self.client = ElevenLabs(api_key=self.api_key)

        # Initialize persistent audio stream and keep-alive thread
        self.SAMPLE_RATE = 22050
        self.CHANNELS = 1
        self.FORMAT = pyaudio.paInt16

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.SAMPLE_RATE,
            frames_per_buffer=1024,
            output=True,
        )
        self._keep_alive = True
        self._playing = threading.Event()
        self._keep_thread = threading.Thread(
            target=self._keep_audio_device_alive,
            daemon=True,
        )
        self._keep_thread.start()

    def reload_config(self) -> None:
        """Reload TTS settings from ``config.yaml`` at runtime."""
        self._load_config()

    def elevenlabs_generate_audio_stream(self, text: str):
        """Return a generator yielding MP3-encoded audio chunks for `text`."""
        # print(f"Generating speech for: {text}")
        # print(f"Using voice ID: {self.voice_id}")
        # print(f"Using model ID: {self.model_id}")
        # print(f"Using output format: {self.output_format}")
        return self.client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            voice_settings=self.voice_settings,
            model_id=self.model_id,
            output_format=self.output_format
        )

    def generate_and_play_advanced(self, text: str):
        """Generate speech for ``text`` and play it using the persistent stream.

        The audio device remains open thanks to a background keep-alive thread,
        so playback begins immediately when this method writes to the stream. A
        timing entry is recorded for both the generation and playback phases.
        """
        generate_start = time.time()
        self.reload_config()
        self._playing.set()
        audio_stream = self.elevenlabs_generate_audio_stream(text)

        # Buffering parameters
        initial_buffer_chunks = 500
        subsequent_buffer_chunks = 500

        mp3_buffer = bytearray()
        chunk_count = 0
        playback_started = False
        play_start = None

        for chunk in audio_stream:
            if not isinstance(chunk, (bytes, bytearray)):
                continue

            mp3_buffer.extend(chunk)
            chunk_count += 1

            # Use a small initial threshold, then the same small chunk size thereafter
            threshold = (
                initial_buffer_chunks
                if chunk_count <= initial_buffer_chunks
                else subsequent_buffer_chunks
            )

            if chunk_count % threshold == 0:
                audio = AudioSegment.from_file(io.BytesIO(mp3_buffer), format="mp3")
                pcm_data = (
                    audio
                    .set_frame_rate(self.SAMPLE_RATE)
                    .set_channels(self.CHANNELS)
                    .set_sample_width(2)
                    .raw_data
                )
                if not playback_started:
                    play_start = time.time()
                    playback_started = True
                self.stream.write(pcm_data)
                mp3_buffer = bytearray()

        # Generation complete
        record_timing("tts_generate", generate_start)

        # Flush any remaining audio
        if mp3_buffer:
            audio = AudioSegment.from_file(io.BytesIO(mp3_buffer), format="mp3")
            pcm_data = (
                audio
                .set_frame_rate(self.SAMPLE_RATE)
                .set_channels(self.CHANNELS)
                .set_sample_width(2)
                .raw_data
            )
            if not playback_started:
                play_start = time.time()
                playback_started = True
            self.stream.write(pcm_data)

        self._playing.clear()

        if playback_started and play_start is not None:
            record_timing("tts_play", play_start)

    def play_mp3_bytes(self, data: bytes) -> None:
        """Play MP3 data using the persistent audio stream."""
        self._playing.set()
        try:
            audio = AudioSegment.from_file(io.BytesIO(data), format="mp3")
            pcm_data = (
                audio
                .set_frame_rate(self.SAMPLE_RATE)
                .set_channels(self.CHANNELS)
                .set_sample_width(2)
                .raw_data
            )
            self.stream.write(pcm_data)
        finally:
            self._playing.clear()

    def _keep_audio_device_alive(self) -> None:
        """Continuously play near-silent audio so the speakers stay active."""
        tone = (
            Sine(60)
            .to_audio_segment(duration=100)
            .apply_gain(-50)
            .set_frame_rate(self.SAMPLE_RATE)
            .set_channels(self.CHANNELS)
            .set_sample_width(2)
        )
        while self._keep_alive:
            if not self._playing.is_set():
                self.stream.write(tone.raw_data)
            time.sleep(0.5)

    def close(self) -> None:
        """Stop background playback and release audio resources."""
        self._keep_alive = False
        if hasattr(self, "_keep_thread") and self._keep_thread.is_alive():
            self._keep_thread.join(timeout=1)
        if hasattr(self, "stream"):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, "p"):
            self.p.terminate()

    def __del__(self):
        """Destructor to ensure resources are released."""
        try:
            self.close()
        except Exception:
            pass


if __name__ == "__main__":
    # Basic sanity check when run directly
    engine = TextToSpeechEngine()
    engine.generate_and_play_advanced("Hello, world! This is a test.")
