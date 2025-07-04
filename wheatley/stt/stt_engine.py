"""Speech-to-text utilities including hotword detection."""

import os
import wave
import numpy as np
import pyaudio
import openai
import yaml
import struct
import pvporcupine
import time
import asyncio
from threading import Event
from utils.timing_logger import record_timing

# ---------------------------------------------------------------------------
# LED colour constants used to signal microphone state on the hardware.  The
# values represent ``(R, G, B)`` tuples that are forwarded to the Arduino via
# ``set_mic_led_color``.
# ``HOTWORD_COLOR``  - waiting for a hotword (blue)
# ``RECORDING_COLOR`` - actively recording speech (green)
# ``PROCESSING_COLOR`` - after recording has stopped (orange)
# ``PAUSED_COLOR``    - microphone paused (red)
# ---------------------------------------------------------------------------
HOTWORD_COLOR = (0, 0, 255)         # blue
RECORDING_COLOR = (0, 255, 0)       # green
PROCESSING_COLOR = (255, 165, 0)    # orange
PAUSED_COLOR = (255, 0, 0)          # red


class SpeechToTextEngine:
    """High-level speech-to-text engine with optional hardware integration."""

    def __init__(self, arduino_interface=None):
        """Initialize the engine and calibrate microphone thresholds."""
        # Load STT settings from the config file
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        stt_config = config.get("stt", {})
        self.CHUNK = stt_config.get("chunk", 1024)
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = stt_config.get("channels", 1)
        self.RATE = stt_config.get("rate", 16000)  # 16kHz is optimal for Whisper
        self.THRESHOLD = 1500  # stt_config.get("threshold", 1500)
        self.SILENCE_LIMIT = 3  # stt_config.get("silence_limit", 2)
        self.arduino_interface = arduino_interface
        self._audio = None
        self._stream = None
        self._porcupine = None
        self._stop_event = Event()
        self._pause_event = Event()
        self._listening = False
        # Set OpenAI API key from config
        openai_api_key = config.get("secrets", {}).get("openai_api_key")
        if not openai_api_key:
            openai_api_key = config.get("openai_api_key")
        if openai_api_key:
            openai.api_key = openai_api_key
            self.api_key = openai_api_key
        else:
            raise ValueError("OpenAI API key not found in config")

        # Ensure the microphone status LED reflects the initial paused state
        self._update_mic_led(PAUSED_COLOR)

        # Calibrate ambient and speech thresholds on startup
        try:
            self.calibrate_threshold()
        except Exception as e:
            print(f"[STT] Threshold calibration failed: {e}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _update_mic_led(self, color):
        """Send ``color`` to the microphone status LED if hardware is present."""
        print(f"[LED] Setting mic LED color to: {color}")
        if self.arduino_interface:
            r, g, b = color
            self.arduino_interface.set_mic_led_color(r, g, b)

    def calibrate_threshold(self, ambient_time: float = 5.0, speech_time: float = 5.0) -> None:
        """Calibrate ``THRESHOLD`` using ambient and spoken audio samples.

        The microphone LED blinks blue during ``ambient_time`` while background
        noise is measured and blinks red during ``speech_time`` while the user
        speaks. The maximum amplitudes from both phases are averaged to derive
        the new threshold.
        """
        self._audio = pyaudio.PyAudio()
        stream = self._audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
        )
        self._stream = stream

        ambient_max = 0
        speech_max = 0

        start = time.time()
        next_toggle = start
        led_on = False
        while time.time() - start < ambient_time:
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            amplitude = np.max(np.abs(np.frombuffer(data, dtype=np.int16)))
            ambient_max = max(ambient_max, amplitude)
            if time.time() >= next_toggle:
                self._update_mic_led(HOTWORD_COLOR if led_on else (0, 0, 0))
                led_on = not led_on
                next_toggle = time.time() + 0.5

        start = time.time()
        next_toggle = start
        led_on = False
        while time.time() - start < speech_time:
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            amplitude = np.max(np.abs(np.frombuffer(data, dtype=np.int16)))
            speech_max = max(speech_max, amplitude)
            if time.time() >= next_toggle:
                self._update_mic_led(PAUSED_COLOR if led_on else (0, 0, 0))
                led_on = not led_on
                next_toggle = time.time() + 0.5

        stream.stop_stream()
        stream.close()
        self._stream = None
        self._audio.terminate()
        self._audio = None
        self._update_mic_led(PAUSED_COLOR)

        if speech_max > ambient_max:
            self.THRESHOLD = int((ambient_max + speech_max) / 2)
        print(f"[STT] Calibration ambient_max={ambient_max} speech_max={speech_max} threshold={self.THRESHOLD}")

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
                print("[STT] Not listening")
            print("[STT] Listening paused.")
        self._update_mic_led(PAUSED_COLOR)

    def resume_listening(self):
        """Resume listening after being paused."""
        if self._pause_event.is_set():
            self._pause_event.clear()
            print("[STT] Listening resumed.")

    def is_paused(self):
        """Return True if listening is paused, False otherwise."""
        return self._pause_event.is_set()

    def connect_stream(self):
        """Connect to the audio input stream, trying different devices if necessary."""
        try:
            self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK, input_device_index=2)
        except Exception:
            try:
                self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK, input_device_index=1)
            except Exception:
                self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK)

    def record_until_silent(self, max_wait_seconds=None):
        """Record audio until silence is detected."""
        start_time = time.time()
        self._audio = pyaudio.PyAudio()
        self.connect_stream()
        frames = []
        silent_frames = 0
        recording = False
        start_time = time.time()
        print("Monitoring...")
        self._update_mic_led(RECORDING_COLOR)

        min_amplitude = float('inf')
        max_amplitude = float('-inf')

        while True:
            data = self._stream.read(self.CHUNK, exception_on_overflow=False)
            data_int = np.frombuffer(data, dtype=np.int16)
            amplitude = np.max(np.abs(data_int))
            min_amplitude = min(min_amplitude, amplitude)
            max_amplitude = max(max_amplitude, amplitude)
            if not recording and max_wait_seconds is not None and (time.time() - start_time) > max_wait_seconds:
                print("No sound detected, aborting...")
                frames = []
                break
            if amplitude > self.THRESHOLD:
                if not recording:
                    print("Sound detected, recording...")
                    recording = True
                    self._update_mic_led(RECORDING_COLOR)
                frames.append(data)
                silent_frames = 0
            else:
                if recording:
                    silent_frames += 1
                    frames.append(data)
                    if silent_frames > (self.RATE / self.CHUNK * self.SILENCE_LIMIT):
                        print("Silence detected, stopping...")
                        break

        print(f"Minimum amplitude: {min_amplitude}")
        print(f"Maximum amplitude: {max_amplitude}")

        self._stream.stop_stream()
        self._stream.close()
        self._stream = None
        self._audio.terminate()
        self._audio = None
        if not frames:
            record_timing("stt_record_until_silent", start_time)
            return None
        self._update_mic_led(PROCESSING_COLOR)

        wav_filename = "temp_recording.wav"
        wf = wave.open(wav_filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        record_timing("stt_record_until_silent", start_time)
        return wav_filename

    def transcribe(self, filename):
        """Transcribe audio file using OpenAI Whisper."""
        start_time = time.time()
        with open(filename, "rb") as audio_file:
            transcription_result = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        record_timing("stt_transcribe", start_time)
        return transcription_result.text

    def record_and_transcribe(self, max_wait_seconds=None):
        """Record audio and transcribe using traditional Whisper API."""
        start_time = time.time()
        wav_file = self.record_until_silent(max_wait_seconds)
        if not wav_file:
            record_timing("stt_record_and_transcribe", start_time)
            return ""
        text = self.transcribe(wav_file)
        os.remove(wav_file)
        record_timing("stt_record_and_transcribe", start_time)
        return text

    def hotword_config(self, keywords=None, sensitivities=None):
        """Return Porcupine configuration for given keywords."""
        if keywords is None:
            keywords = ["computer", "jarvis"]
        if sensitivities is None:
            sensitivities = [0.5] * len(keywords)
        try:
            self._porcupine = pvporcupine.create(
                access_key=self.api_key,
                keyword_paths=["stt/wheatley.ppn"]
            )
        except Exception:
            self._porcupine = pvporcupine.create(
                access_key=self.api_key,
                keywords=keywords,
                sensitivities=sensitivities
            )

    def listen_for_hotword(self, access_key=None, keywords=None, sensitivities=None):
        """Block until one of ``keywords`` is heard.

        Parameters
        ----------
        access_key : str, optional
            Porcupine API key. If ``None`` it is read from the config file.
        keywords : list[str], optional
            List of wake words to detect. Defaults to ``["computer", "jarvis"]``.
        sensitivities : list[float], optional
            Sensitivity per keyword (0..1).

        Returns
        -------
        int | None
            Index of detected keyword or ``None`` if listening was interrupted.
        """
        start_time = time.time()
        if access_key is None:
            # Try to load from config
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            access_key = config.get("stt", {}).get("porcupine_api_key")
        if not access_key:
            print("Porcupine API key not found in config. Hotword detection disabled.")
            record_timing("stt_listen_hotword", start_time)
            return None
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
        print(f"[Hotword] Listening for hotword(s): {keywords}")
        self._update_mic_led(HOTWORD_COLOR)
        self._listening = True
        print("[STT] Listening")
        detected_index = None
        try:
            while True:
                if self._pause_event.is_set():
                    break
                pcm = stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                pcm_unpacked = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
                keyword_index = self._porcupine.process(pcm_unpacked)
                if keyword_index >= 0:
                    print(f"[Hotword] Detected: {keywords[keyword_index]}")
                    detected_index = keyword_index
                    break
                # Status update every 10 seconds
                if time.time() % 10 < 0.03:
                    print("[Hotword] Still listening...")
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
            if self._listening:
                self._listening = False
                print("[STT] Not listening")
            self._update_mic_led(PAUSED_COLOR)
        record_timing("stt_listen_hotword", start_time)
        return detected_index

    def get_voice_input(self):
        """Wait for hotword, then record and transcribe speech. Return transcribed text or empty string if nothing detected."""
        idx = self.listen_for_hotword()
        if idx is None:
            return ""
        wav_file = self.record_until_silent()
        if not wav_file:
            print("No audio detected.")
            return ""
        self._update_mic_led(PROCESSING_COLOR)
        text = self.transcribe(wav_file)
        os.remove(wav_file)
        return text

    async def hotword_listener(self, queue):
        """Background task that records speech after a hotword trigger."""
        print("[Hotword] Background listener started.")
        loop = asyncio.get_event_loop()
        try:
            while True:
                if self.is_paused():
                    await asyncio.sleep(0.1)
                    continue
                text = await loop.run_in_executor(None, self.get_voice_input)
                if text and text.strip():
                    await queue.put({"type": "voice", "text": text.strip()})
        except asyncio.CancelledError:
            print("[Hotword] Listener cancelled.")
        except Exception as e:
            print(f"[Hotword] Listener error: {e}")

    def cleanup(self):
        """Clean up any open audio streams, PyAudio instances, and Porcupine resources."""
        self._stop_event.set()
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._audio is not None:
            try:
                self._audio.terminate()
            except Exception:
                pass
            self._audio = None
        if self._porcupine is not None:
            try:
                self._porcupine.delete()
            except Exception:
                pass
            self._porcupine = None
        self._update_mic_led(PAUSED_COLOR)


if __name__ == "__main__":
    # Basic manual test when running this module directly
    engine = SpeechToTextEngine()
    try:
        result = engine.record_and_transcribe(5)
        print(f"Transcribed: {result}")
    finally:
        engine.cleanup()
