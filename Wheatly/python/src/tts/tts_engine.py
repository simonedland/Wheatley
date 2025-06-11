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
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings


class TextToSpeechEngine:
    def __init__(self):
        # Load configuration once during initialization to keep TTS calls fast
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "config.yaml"
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
            speed=tts_config.get("speed", 0.8)
        )
        self.model_id = tts_config.get("model_id", "eleven_flash_v2_5")
        self.output_format = tts_config.get("output_format", "mp3_22050_32")

        # Silence noisy logging from the ElevenLabs library
        logging.getLogger("elevenlabs").setLevel(logging.WARNING)

        # Reuse one API client for all requests
        self.client = ElevenLabs(api_key=self.api_key)

    def elevenlabs_generate_audio_stream(self, text: str):
        """Return a generator yielding MP3-encoded audio chunks for `text`."""
        return self.client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            voice_settings=self.voice_settings,
            model_id=self.model_id,
            output_format=self.output_format
        )

    def generate_and_play_advanced(self, text: str):
        """
        Generate speech for `text` and play it back immediately using streaming.
        Starts playback almost instantly by pre-warming the audio device
        with a tiny beep and using a small initial buffer.
        """
        start_time = time.time()
        audio_stream = self.elevenlabs_generate_audio_stream(text)

        # Playback parameters
        SAMPLE_RATE = 22050
        CHANNELS = 1
        FORMAT = pyaudio.paInt16

        # 1) Open & warm up the audio device
        p = pyaudio.PyAudio()
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            frames_per_buffer=1024,
            output=True
        )
        # Play a very short 30Hz beep to wake up the hardware
        #beep = (
        #    Sine(60)
        #    .to_audio_segment(duration=1000)  # 20ms tone
        #    .set_frame_rate(SAMPLE_RATE)
        #    .set_channels(CHANNELS)
        #    .set_sample_width(2)
        #)
        #stream.write(beep.raw_data)

        #add a second of silence to ensure the device is ready
        #silence = AudioSegment.silent(duration=1000)
        #stream.write(silence.raw_data)

        # 2) Buffer a small number of chunks before first playback
        INITIAL_BUFFER_CHUNKS = 500
        SUBSEQUENT_BUFFER_CHUNKS = 500

        mp3_buffer = bytearray()
        chunk_count = 0

        for chunk in audio_stream:
            if not isinstance(chunk, (bytes, bytearray)):
                continue

            mp3_buffer.extend(chunk)
            chunk_count += 1

            # Use a small initial threshold, then the same small chunk size thereafter
            threshold = (
                INITIAL_BUFFER_CHUNKS
                if chunk_count <= INITIAL_BUFFER_CHUNKS
                else SUBSEQUENT_BUFFER_CHUNKS
            )

            if chunk_count % threshold == 0:
                audio = AudioSegment.from_file(io.BytesIO(mp3_buffer), format="mp3")
                pcm_data = (
                    audio
                    .set_frame_rate(SAMPLE_RATE)
                    .set_channels(CHANNELS)
                    .set_sample_width(2)
                    .raw_data
                )
                stream.write(pcm_data)
                mp3_buffer = bytearray()

        # Flush any remaining audio
        if mp3_buffer:
            audio = AudioSegment.from_file(io.BytesIO(mp3_buffer), format="mp3")
            pcm_data = (
                audio
                .set_frame_rate(SAMPLE_RATE)
                .set_channels(CHANNELS)
                .set_sample_width(2)
                .raw_data
            )
            stream.write(pcm_data)

        # Clean up
        stream.stop_stream()
        stream.close()
        p.terminate()

        record_timing("tts_generate_and_play", start_time)


if __name__ == "__main__":
    # Basic sanity check when run directly
    engine = TextToSpeechEngine()
    engine.generate_and_play_advanced("Hello, world! This is a test.")
