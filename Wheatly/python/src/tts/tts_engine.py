"""Simple wrapper around the ElevenLabs TTS API.

This module exposes :class:`TextToSpeechEngine` which converts text to
speech using the ElevenLabs API and plays the result back.  The class is
configured via ``config/config.yaml`` and keeps the interface minimal so
that it can be reused throughout the project.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from tempfile import NamedTemporaryFile
from utils.timing_logger import record_timing
import time

from playsound import playsound
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

class TextToSpeechEngine:
    def __init__(self):
        import yaml
        # Load configuration once during initialisation.  This keeps runtime
        # overhead low when generating audio.
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml"
        )
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Extract relevant TTS parameters from config
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
        # Silence noisy logging from the underlying library
        logging.getLogger("elevenlabs").setLevel(logging.WARNING)

        # API client instance reused for every request
        self.client = ElevenLabs(api_key=self.api_key)
    
    def elevenlabs_generate_audio(self, text: str):
        """Return a generator yielding audio chunks for ``text``."""
        return self.client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            voice_settings=self.voice_settings,
            model_id=self.model_id,
            output_format=self.output_format
        )
    
    def generate_and_play_advanced(self, text: str):
        """Generate speech for ``text`` and play it back immediately."""

        start_time = time.time()
        audio_chunks = list(self.elevenlabs_generate_audio(text))

        # Use a temporary file so the OS cleans it up automatically
        with NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            for chunk in audio_chunks:
                temp_file.write(chunk)
            temp_file.flush()
            file_path = temp_file.name

        try:
            playsound(file_path)
        except Exception as exc:  # pragma: no cover - playback depends on host
            logging.error("Error playing audio file: %s", exc)
        finally:
            try:
                os.remove(file_path)
            except OSError as exc:  # pragma: no cover - file may already be gone
                logging.error("Error deleting audio file: %s", exc)
        record_timing("tts_generate_and_play", start_time)

if __name__ == "__main__":
    # Basic sanity check when run directly
    engine = TextToSpeechEngine()
    engine.generate_and_play_advanced("Hello, world! This is a test.")
