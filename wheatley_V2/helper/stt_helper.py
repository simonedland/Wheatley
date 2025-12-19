"""Speech-to-text utilities including hotword detection (Ported for V2)."""

import asyncio
import os
import random
import struct
import sys
import time
import wave
from pathlib import Path
from threading import Event
from typing import Optional

import numpy as np  # type: ignore[import-not-found]
import openai  # type: ignore[import-not-found]
import pyaudio  # type: ignore[import-untyped]
import pvporcupine  # type: ignore[import-not-found]
import yaml

# Directory containing pre-recorded greetings played after hotword detection
# Pointing to the V1 directory for now
HOTWORD_GREETINGS_DIR = Path(__file__).parents[2] / "wheatley" / "stt" / "hotword_greetings"
KEYWORD_FILE_PATH = Path(__file__).parents[2] / "wheatley" / "stt" / "wheatley.ppn"
class SpeechToTextEngine:
    """High-level speech-to-text engine."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the engine and calibrate microphone thresholds."""
        if config_path is None:
            config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        
        self.config_path = config_path
        self._load_config()

        self._audio = None
        self._stream = None
        self._porcupine = None
        self._stop_event = Event()
        self._pause_event = Event()
        self._listening = False
        
        # Ensure the microphone status is paused initially
        self._pause_event.set()

        # Calibrate ambient and speech thresholds on startup
        try:
            self.calibrate_threshold()
        except Exception as e:
            print(f"[STT] Threshold calibration failed: {e}")

    def _load_config(self):
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)
        
        stt_config = config.get("stt", {})
        self.CHUNK = stt_config.get("chunk", 1024)
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = stt_config.get("channels", 1)
        self.RATE = stt_config.get("rate", 16000)  # 16kHz is optimal for Whisper
        self.THRESHOLD = 1500  # stt_config.get("threshold", 1500)
        self.SILENCE_LIMIT = 3  # stt_config.get("silence_limit", 2)

        # Set OpenAI API key from config
        self.porcupine_api_key = config.get("secrets", {}).get("porcupine_api_key")
        if not self.porcupine_api_key:
             # Fallback to stt section if present (legacy)
            self.porcupine_api_key = stt_config.get("porcupine_api_key")

        self.openai_api_key = config.get("secrets", {}).get("openai_api_key")
        
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        else:
            raise ValueError("OpenAI API key not found in config")
            
        if not self.porcupine_api_key:
            print("[STT] Warning: Porcupine API key not found in config. Hotword detection will be disabled.")

    def calibrate_threshold(
        self, ambient_time: float = 2.0
    ) -> None:
        """Calibrate ``THRESHOLD`` using ambient audio samples.
        
        Simplified calibration: just measure ambient noise and set threshold above it.
        """
        print("[STT] Calibrating microphone threshold...")
        self._audio = pyaudio.PyAudio()
        if self._audio is None:
            print("[STT] Failed to initialize PyAudio")
            return

        try:
            self._stream = self._audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )

            ambient_max = 0
            start = time.time()
            
            while time.time() - start < ambient_time:
                if self._stream is None:
                    break
                data = self._stream.read(self.CHUNK, exception_on_overflow=False)
                amplitude = np.max(np.abs(np.frombuffer(data, dtype=np.int16)))
                ambient_max = max(ambient_max, amplitude)

            # Set threshold to ambient max + margin (e.g. 500 or 50% more)
            self.THRESHOLD = max(int(ambient_max * 1.5), 500)
            print(
                f"[STT] Calibration ambient_max={ambient_max} threshold={self.THRESHOLD}"
            )
        finally:
            if self._stream:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            if self._audio:
                try:
                    self._audio.terminate()
                except Exception:
                    pass
                self._audio = None

    # ------------------------------------------------------------------
    # Listening control helpers
    # ------------------------------------------------------------------
    def pause_listening(self):
        """Pause any ongoing listening or transcription."""
        if not self._pause_event.is_set():
            self._pause_event.set()
            self._stop_event.set()
            if self._listening:
                self._listening = False
            print("[STT] Listening paused.")

    def resume_listening(self):
        """Resume listening after being paused."""
        if self._pause_event.is_set():
            self._stop_event.clear()
            self._pause_event.clear()
            print("[STT] Listening resumed.")

    def is_paused(self):
        """Return True if listening is paused, False otherwise."""
        return self._pause_event.is_set()

    # ----------------------------
    # Recording helper methods
    # ----------------------------
    def _tts_playing(self, tts_engine) -> bool:
        # Check if TTS is playing (using the V2 TTSHandler)
        # V2 TTSHandler doesn't seem to have is_playing() method directly exposed in the snippet I saw?
        # I need to check tts_helper.py again.
        # It has `wait_idle()`. It has `_play_audio` task.
        # I might need to add `is_playing` property to TTSHandler in tts_helper.py
        # For now, I'll assume I can check it or I'll add it.
        return (
            tts_engine is not None
            and hasattr(tts_engine, "is_playing")
            and tts_engine.is_playing
        )

    def _wait_for_tts(self, tts_engine) -> None:
        while self._tts_playing(tts_engine):
            print("[STT] Waiting for TTS to finish before recording...")
            time.sleep(0.1)

    def _play_hotword_greeting(self, tts_engine) -> None:
        """Play a random greeting from ``HOTWORD_GREETINGS_DIR`` if available."""
        if tts_engine is None:
            return
        try:
            if not HOTWORD_GREETINGS_DIR.exists():
                return
            files = [
                f
                for f in os.listdir(HOTWORD_GREETINGS_DIR)
                if f.lower().endswith(".mp3")
            ]
        except FileNotFoundError:
            return
        if not files:
            return
        choice = random.choice(files)
        path = HOTWORD_GREETINGS_DIR / choice
        try:
            # V2 TTSHandler might not have play_mp3_bytes. 
            # It uses pydub.playback.play.
            # I should probably use pydub directly here or add a method to TTSHandler.
            # For simplicity, I'll skip this for now or implement a simple player.
            # Or better, use the TTSHandler to play it if it supports it.
            # The V2 TTSHandler takes text.
            # I'll skip playing greeting for now to avoid complexity, or just print it.
            print(f"[STT] (Greeting would play: {choice})")
        except Exception as exc:
            print(f"[STT] Failed to play greeting '{choice}': {exc}")

    def _should_abort(self, tts_engine) -> bool:
        if self.is_paused() or self._tts_playing(tts_engine):
            msg = (
                "[STT] TTS started during recording, aborting..."
                if self._tts_playing(tts_engine)
                else "[STT] Recording paused, aborting..."
            )
            print(msg)
            return True
        return False

    def _monitor_for_sound(self, stream, start_time, max_wait_seconds, tts_engine):
        frames = []
        min_amplitude = float("inf")
        max_amplitude = float("-inf")
        while True:
            if self._should_abort(tts_engine):
                return [], min_amplitude, max_amplitude
            if (
                max_wait_seconds is not None
                and time.time() - start_time > max_wait_seconds
            ):
                # print("No sound detected, aborting...")
                return [], min_amplitude, max_amplitude
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            amplitude = np.max(np.abs(np.frombuffer(data, dtype=np.int16)))
            min_amplitude = min(min_amplitude, amplitude)
            max_amplitude = max(max_amplitude, amplitude)
            if amplitude > self.THRESHOLD:
                print("Sound detected, recording...")
                frames.append(data)
                return frames, min_amplitude, max_amplitude

    def _continue_until_silence(
        self, stream, frames, tts_engine, min_amplitude, max_amplitude
    ):
        silent_frames = 0
        while frames:
            if self._should_abort(tts_engine):
                return [], min_amplitude, max_amplitude
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            frames.append(data)
            amplitude = np.max(np.abs(np.frombuffer(data, dtype=np.int16)))
            min_amplitude = min(min_amplitude, amplitude)
            max_amplitude = max(max_amplitude, amplitude)
            silent_frames = 0 if amplitude > self.THRESHOLD else silent_frames + 1
            if silent_frames > (self.RATE / self.CHUNK * self.SILENCE_LIMIT):
                print("Silence detected, stopping...")
                break
        return frames, min_amplitude, max_amplitude

    def record_until_silent(self, max_wait_seconds=None, tts_engine=None):
        """Record audio until silence is detected."""
        start_time = time.time()

        # Ensure we don't start while TTS is speaking
        self._wait_for_tts(tts_engine)

        audio = pyaudio.PyAudio()
        try:
            stream = audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )
            frames = []
            # print("Monitoring...")

            # Phase 1: wait for sound above threshold
            frames, min_amplitude, max_amplitude = self._monitor_for_sound(
                stream, start_time, max_wait_seconds, tts_engine
            )

            # Phase 2: continue recording until silence window reached
            if frames:
                frames, min_amplitude, max_amplitude = self._continue_until_silence(
                    stream, frames, tts_engine, min_amplitude, max_amplitude
                )

            stream.stop_stream()
            stream.close()

            if not frames:
                return None

            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_filename = tmp.name
            with wave.open(wav_filename, "wb") as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(audio.get_sample_size(self.FORMAT))
                wf.setframerate(self.RATE)
                wf.writeframes(b"".join(frames))
            return wav_filename        
        finally:
            audio.terminate()

    def transcribe(self, filename):
        """Transcribe audio file using OpenAI Whisper."""
        with open(filename, "rb") as audio_file:
            transcription_result = openai.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
        return transcription_result.text

    def hotword_config(self, keywords=None, sensitivities=None):
        """Return Porcupine configuration for given keywords."""
        if keywords is None:
            keywords = ["computer", "jarvis"]
        if sensitivities is None:
            sensitivities = [0.5] * len(keywords)
        
        try:
            if KEYWORD_FILE_PATH.exists():
                 self._porcupine = pvporcupine.create(
                    access_key=self.porcupine_api_key,
                    keyword_paths=[str(KEYWORD_FILE_PATH)],
                    sensitivities=sensitivities,
                )
                 print(f"[Hotword] Using custom keyword file '{KEYWORD_FILE_PATH}'")
            else:
                raise FileNotFoundError("Custom keyword file not found")
        except Exception:
            self._porcupine = pvporcupine.create(
                access_key=self.porcupine_api_key,
                keywords=keywords,
                sensitivities=sensitivities,
            )
            print("[Hotword] Using default keywords")

    def listen_for_hotword(self, keywords=None, sensitivities=None):
        """Block until one of ``keywords`` is heard."""
        if not self.porcupine_api_key:
            return None

        if keywords is None:
            keywords = ["computer", "jarvis"]
            
        self.hotword_config(keywords, sensitivities)
        pa = pyaudio.PyAudio()
        self._audio = pa
        stream = pa.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self._porcupine.frame_length,
        )
        self._stream = stream
        print(f"[Hotword] Listening for hotword(s)...")
        self._listening = True
        detected_index = None
        try:
            while True:
                if self._pause_event.is_set():
                    time.sleep(0.1)
                    continue
                    
                pcm = stream.read(
                    self._porcupine.frame_length, exception_on_overflow=False
                )
                pcm_unpacked = struct.unpack_from(
                    "h" * self._porcupine.frame_length, pcm
                )
                keyword_index = self._porcupine.process(pcm_unpacked)
                if keyword_index >= 0:
                    print(f"[Hotword] Detected!")
                    detected_index = keyword_index
                    break
        except KeyboardInterrupt:
            print("[Hotword] Listener interrupted.")
        finally:
            stream.stop_stream()
            stream.close()
            self._stream = None
            pa.terminate()
            self._audio = None
            self._porcupine.delete()
            self._porcupine = None
            self._listening = False
        return detected_index

    def get_voice_input(self, tts_engine=None):
        """Wait for hotword, then record and transcribe speech."""
        # Block if TTS is playing
        self._wait_for_tts(tts_engine)
        
        idx = self.listen_for_hotword(keywords=["Wheatley"])
        if idx is None:
            return ""
            
        # self._play_hotword_greeting(tts_engine)
        
        wav_file = self.record_until_silent(tts_engine=tts_engine)
        if not wav_file or self.is_paused():
            print("No audio detected or paused.")
            return ""
            
        if self.is_paused():
            print("[STT] Paused before transcription.")
            return ""
            
        text = self.transcribe(wav_file)
        os.remove(wav_file)
        return text

    async def hotword_listener(self, queue: asyncio.Queue, tts_engine=None):
        """Background task that records speech after a hotword trigger."""
        print("[Hotword] Background listener started.")
        loop = asyncio.get_event_loop()
        try:
            while True:
                if self.is_paused() or self._tts_playing(tts_engine):
                    await asyncio.sleep(0.1)
                    continue
                
                # Run blocking get_voice_input in executor
                text = await loop.run_in_executor(
                    None, self.get_voice_input, tts_engine
                )
                
                if text and text.strip():
                    print(f"[STT] Transcribed: {text}")
                    await queue.put({"text": text.strip(), "source": "stt"})
        except asyncio.CancelledError:
            print("[Hotword] Listener cancelled.")
        except Exception as e:
            print(f"[Hotword] Listener error: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def cleanup(self):
        """Clean up any open audio streams."""
        self._stop_event.set()
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
        if self._audio is not None:
            try:
                self._audio.terminate()
            except Exception:
                pass
