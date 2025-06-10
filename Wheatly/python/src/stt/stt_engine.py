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
    def __init__(self, arduino_interface=None):
        # Load STT settings from the config file
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        stt_config = config.get("stt", {})
        self.CHUNK = stt_config.get("chunk", 1024)
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = stt_config.get("channels", 1)
        self.RATE = stt_config.get("rate", 16000)  # 16kHz is optimal for Whisper
        self.THRESHOLD = 100 #stt_config.get("threshold", 1500)
        self.SILENCE_LIMIT = 3 #stt_config.get("silence_limit", 2)
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _update_mic_led(self, color):
        """Send ``color`` to the microphone status LED if hardware is present."""
        print(f"[LED] Setting mic LED color to: {color}")
        if self.arduino_interface:
            r, g, b = color
            self.arduino_interface.set_mic_led_color(r, g, b)

    # ------------------------------------------------------------------
    # Listening control helpers
    # ------------------------------------------------------------------
    def pause_listening(self):
        """Pause any ongoing listening/transcription."""
        if not self._pause_event.is_set():
            self._pause_event.set()
            self._stop_event.set()
            if self._listening:  # If the system is currently listening, update the state
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
        return self._pause_event.is_set()



    # Legacy methods for backward compatibility
    def record_until_silent(self, max_wait_seconds=None):
        """Record audio until silence is detected.

        Parameters
        ----------
        max_wait_seconds: float or None
            Optional timeout. If no sound is detected within this many
            seconds the method returns ``None`` and stops listening. This
            allows callers to fall back to hotword detection after a period
            of silence.
        """
        self._audio = pyaudio.PyAudio()
        try:
            self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK, input_device_index=2)
        except:
            try:
                self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK, input_device_index=1)
            except:
                self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK)
        
        frames = []
        silent_frames = 0
        recording = False
        start_time = time.time()
        print("Monitoring...")

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
            return None
        self._update_mic_led(PROCESSING_COLOR)

        wav_filename = "temp_recording.wav"
        wf = wave.open(wav_filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        return wav_filename

    def transcribe(self, filename):
        """Transcribe audio file using OpenAI Whisper"""
        with open(filename, "rb") as audio_file:
            transcription_result = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcription_result.text

    def record_and_transcribe(self, max_wait_seconds=None):
        """Record audio and transcribe using traditional Whisper API"""
        wav_file = self.record_until_silent(max_wait_seconds)
        if not wav_file:
            return ""
        text = self.transcribe(wav_file)
        os.remove(wav_file)
        return text

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
        if access_key is None:
            # Try to load from config
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            access_key = config.get("stt", {}).get("porcupine_api_key")
        if not access_key:
            print("Porcupine API key not found in config. Hotword detection disabled.")
            return None
        if keywords is None:
            keywords = ["computer", "jarvis"]
        if sensitivities is None:
            sensitivities = [0.5] * len(keywords)
        
        self._porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=keywords,
            sensitivities=sensitivities
        )
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
        try:
            while True:
                if self._pause_event.is_set():
                    break
                pcm = stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                pcm_unpacked = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
                keyword_index = self._porcupine.process(pcm_unpacked)
                if keyword_index >= 0:
                    print(f"[Hotword] Detected: {keywords[keyword_index]}")
                    return keyword_index
                # Status update every 10 seconds
                # Periodic status updates so the user knows we're alive
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
            # Reflect current state on the microphone LED
            if self.is_paused():
                self._update_mic_led(PAUSED_COLOR)
            else:
                self._update_mic_led(HOTWORD_COLOR)

        return None


    def get_voice_input(self):
        """
        Waits for hotword, then records and transcribes speech.
        Returns the transcribed text, or empty string if nothing detected.
        """
        idx = self.listen_for_hotword()
        if idx is None:
            return ""
        wav_file = self.record_until_silent()
        if not wav_file:
            print("No audio detected.")
            self._update_mic_led(HOTWORD_COLOR)
            return ""
        self._update_mic_led(PROCESSING_COLOR)
        text = self.transcribe(wav_file)
        os.remove(wav_file)
        self._update_mic_led(HOTWORD_COLOR)
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
        """
        Cleanup any open audio streams, PyAudio instances, and Porcupine resources.
        """
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
