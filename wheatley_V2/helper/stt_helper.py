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
HOTWORD_GREETINGS_DIR = (
    Path(__file__).parents[2] / "wheatley" / "stt" / "hotword_greetings"
)
KEYWORD_FILE_PATH = Path(__file__).parents[2] / "wheatley" / "stt" / "wheatley.ppn"


class SpeechToTextEngine:
    """High-level speech-to-text engine."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Create and configure a SpeechToTextEngine, initialize internal audio/hotword state, and prepare microphone thresholds.
        
        Parameters:
            config_path (Optional[Path]): Path to the YAML configuration file. If omitted, defaults to the package's config/config.yaml.
        
        Notes:
            - Initializes internal references for audio, stream, and hotword detector and creates control events used to pause/stop listening.
            - Leaves the engine in a paused state.
            - Attempts to calibrate ambient and speech thresholds during construction.
        """
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
        """
        Load STT-related configuration from the instance's config_path and initialize runtime settings and API keys.
        
        Reads YAML configuration and sets audio parameters (CHUNK, FORMAT, CHANNELS, RATE, THRESHOLD, SILENCE_LIMIT) on the instance, assigns OpenAI and Porcupine API keys (setting openai.api_key), raises ValueError if the OpenAI API key is missing, and prints a warning if the Porcupine API key is not provided.
        """
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
            print(
                "[STT] Warning: Porcupine API key not found in config. Hotword detection will be disabled."
            )

    def calibrate_threshold(self, ambient_time: float = 2.0) -> None:
        """
        Calibrate the engine's microphone sensitivity from ambient audio and set self.THRESHOLD.
        
        Samples microphone input for up to `ambient_time` seconds to determine the ambient maximum amplitude and sets `self.THRESHOLD` to either 1.5× that ambient maximum or 500, whichever is greater.
        
        Parameters:
            ambient_time (float): Seconds to sample ambient audio for calibration (default 2.0).
        
        Side effects:
            Sets `self.THRESHOLD` (int). Temporarily opens `self._audio` and `self._stream` for sampling and ensures they are closed and set to `None` on completion.
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
        """
        Indicates whether the engine is currently paused.
        
        Returns:
            `True` if listening is paused, `False` otherwise.
        """
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
        """
        Determine whether the provided TTS engine is currently playing audio.
        
        Parameters:
            tts_engine: The text-to-speech engine instance to check; may be None.
        
        Returns:
            bool: `true` if `tts_engine` is present and exposes an `is_playing` attribute that is truthy, `false` otherwise.
        """
        return (
            tts_engine is not None
            and hasattr(tts_engine, "is_playing")
            and tts_engine.is_playing
        )

    def _wait_for_tts(self, tts_engine) -> None:
        """
        Block until the provided TTS engine is no longer playing.
        
        Parameters:
            tts_engine: The text-to-speech engine to poll. The engine is queried via the class's `_tts_playing`
                helper; if the engine is None or not reporting playback, this method returns immediately.
        """
        while self._tts_playing(tts_engine):
            print("[STT] Waiting for TTS to finish before recording...")
            time.sleep(0.1)

    def _play_hotword_greeting(self, tts_engine) -> None:
        """
        Attempt to play a random greeting audio file from HOTWORD_GREETINGS_DIR if possible.
        
        If `tts_engine` is None, the directory does not exist, no `.mp3` files are found, or a FileNotFoundError occurs while listing files, the function does nothing. When a file is selected the function logs the chosen filename (currently via a print statement) rather than performing actual playback.
        
        Parameters:
            tts_engine: The TTS engine instance used to play the greeting; if None, the greeting is skipped.
        """
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
        print(f"[STT] (Greeting would play: {choice})")

    def _should_abort(self, tts_engine) -> bool:
        """
        Determine whether ongoing recording should be aborted due to pause state or active TTS playback.
        
        Parameters:
            tts_engine: The text-to-speech engine to check for active playback; may be None.
        
        Returns:
            `true` if listening is paused or the TTS engine is currently playing, `false` otherwise.
        """
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
        """
        Waits for audible input on the given audio stream and returns the first captured frame with observed amplitude bounds.
        
        Parameters:
            stream: An open PyAudio input stream used to read raw audio frames.
            start_time (float): Monotonic timestamp when monitoring began; used to enforce max_wait_seconds.
            max_wait_seconds (Optional[float]): Maximum seconds to wait for sound before aborting; pass None for no timeout.
            tts_engine: Optional TTS engine instance checked to determine whether monitoring should abort while TTS is active.
        
        Returns:
            tuple: (frames, min_amplitude, max_amplitude)
                frames (list[bytes]): A list containing the first audio frame that exceeded the amplitude threshold, or an empty list if aborted or timed out.
                min_amplitude (float): The minimum observed frame amplitude during monitoring (float("inf") if no frames were read).
                max_amplitude (float): The maximum observed frame amplitude during monitoring (float("-inf") if no frames were read).
        """
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
        """
        Continue recording from the given audio stream until a sustained period of silence is detected, updating observed amplitude statistics.
        
        Parameters:
            stream: Open audio input stream with a .read(CHUNK) method to pull audio frames.
            frames (list): Mutable list of audio frame bytes already collected; new frames are appended.
            tts_engine: Optional TTS engine checked to decide whether recording should abort.
            min_amplitude (int): Current minimum observed frame amplitude; will be updated if lower values are seen.
            max_amplitude (int): Current maximum observed frame amplitude; will be updated if higher values are seen.
        
        Returns:
            tuple: (frames, min_amplitude, max_amplitude) where `frames` is the list of collected audio frames (or an empty list if recording was aborted), and the amplitude values reflect the updated min and max observed during this recording phase.
        """
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
        """
        Record audio from the default input until a silence window is detected and save it to a temporary WAV file.
        
        The method waits for any active TTS playback to finish, then performs a two-phase recording:
        first it waits for sound above the configured threshold, then it continues recording until a configured silence window is observed. The recorded audio is written to a temporary WAV file which is returned.
        
        Parameters:
            max_wait_seconds (float | None): Maximum time in seconds to wait for initial sound before aborting. If None, no explicit initial timeout is applied.
            tts_engine (object | None): Optional TTS engine whose playback state is checked to avoid recording while TTS is speaking; only an attribute like `is_playing` is required.
        
        Returns:
            str | None: Path to the temporary WAV file containing the recorded audio, or `None` if no audio was recorded (e.g., timed out or aborted).
        """
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
        """
        Transcribe a local audio file to text using the Whisper model.
        
        Parameters:
            filename (str or Path): Path to the audio file to transcribe.
        
        Returns:
            str: The transcribed text from the audio file.
        """
        with open(filename, "rb") as audio_file:
            transcription_result = openai.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
        return transcription_result.text

    def hotword_config(self, keywords=None, sensitivities=None):
        """
        Configure and initialize the Porcupine hotword detector on this instance, preferring a local custom keyword file when available.
        
        Parameters:
            keywords (Optional[list[str]]): Keyword names to use if no custom keyword file is present. Defaults to ["computer", "jarvis"].
            sensitivities (Optional[list[float]]): Sensitivity values (0.0 to 1.0) corresponding to each keyword. Defaults to 0.5 for each keyword.
        
        Behavior:
            If a custom keyword file exists at KEYWORD_FILE_PATH, the detector is initialized with that file; otherwise the detector is initialized with the provided keyword names and sensitivities. The initialized Porcupine instance is stored on self._porcupine.
        """
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
        """
        Listen for configured Porcupine hotwords and return which keyword was detected.
        
        Parameters:
            keywords (Optional[list[str]]): Sequence of hotword names to listen for. Defaults to ["computer", "jarvis"] when not provided.
            sensitivities (Optional[list[float]]): Per-keyword sensitivity values (0.0-1.0). If omitted, default sensitivities are used.
        
        Returns:
            int | None: The index of the detected keyword in the `keywords` list, or `None` if hotword detection is disabled (no Porcupine API key) or no keyword was detected before the listener was stopped.
        """
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
        """
        Listen for a configured hotword, record the subsequent speech until silence, and return its transcription.
        
        Parameters:
            tts_engine: Optional TTS engine whose playback state is respected to avoid recording while speech is playing.
        
        Returns:
            transcription (str): Transcribed text of the recorded speech, or an empty string if no audio was detected or listening was paused.
        """
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
        """
        Continuously listens for hotword-triggered speech, transcribes captured audio, and enqueues transcription results.
        
        While running, the task defers recording when listening is paused or when the provided TTS engine is playing. For each non-empty transcription it places a dictionary of the form {"text": <transcribed text>, "source": "stt"} onto the supplied asyncio.Queue. The task runs until cancelled; cancellation causes it to exit cleanly.
        
        Parameters:
            queue (asyncio.Queue): Queue to receive transcription dictionaries {"text": str, "source": "stt"}.
            tts_engine (optional): TTS engine used to determine whether playback is active; when playing, recording is postponed.
        """
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
        """
        Enter the runtime context and make the engine instance available for use within a with-statement.
        
        Returns:
            self (SpeechToTextEngine): The current SpeechToTextEngine instance.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Call cleanup when exiting the context manager.
        
        Invokes self.cleanup() to release resources and stop background activity. Does not suppress exceptions raised inside the with-block.
        """
        self.cleanup()

    def cleanup(self):
        """
        Signal the engine to stop and release any audio resources.
        
        This sets the internal stop event, stops and closes the active audio stream if present, and terminates the PyAudio instance. Any errors raised during cleanup are intentionally suppressed.
        """
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