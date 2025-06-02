import os
import wave
import numpy as np
import pyaudio
import openai
import yaml
import struct
import pvporcupine
import time

class SpeechToTextEngine:
    def __init__(self):
        # Load STT settings from the config file
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        stt_config = config.get("stt", {})
        self.CHUNK = stt_config.get("chunk", 1024)
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = stt_config.get("channels", 1)
        self.RATE = stt_config.get("rate", 44100)
        self.THRESHOLD = stt_config.get("threshold", 3000)
        self.SILENCE_LIMIT = stt_config.get("silence_limit", 1)
        self._audio = None
        self._stream = None
        self._porcupine = None
        # Set OpenAI API key from config
        openai_api_key = config.get("secrets", {}).get("openai_api_key")
        if not openai_api_key:
            openai_api_key = config.get("openai_api_key")
        if openai_api_key:
            openai.api_key = openai_api_key

    def dry_run(self, filename):
        # Recognize speech using Whisper model deployed in Azure (dry run)
        # TODO: Replace the following with the actual call to Azure's deployed Whisper service
        return "Dry run: recognized text from Whisper model on Azure (simulated)"

    def record_until_silent(self):
        """Record audio until silence is detected."""
        self._audio = pyaudio.PyAudio()
        try:
            self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK, input_device_index=2)
        except:
            self._stream = self._audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK, input_device_index=1)
        frames = []
        silent_frames = 0
        recording = False
        print("Monitoring...")

        min_amplitude = float('inf')
        max_amplitude = float('-inf')

        while True:
            data = self._stream.read(self.CHUNK, exception_on_overflow = False)
            data_int = np.frombuffer(data, dtype=np.int16)
            amplitude = np.max(np.abs(data_int))
            min_amplitude = min(min_amplitude, amplitude)
            max_amplitude = max(max_amplitude, amplitude)
            if amplitude > self.THRESHOLD:
                if not recording:
                    print("Sound detected, recording...")
                    recording = True
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
        wav_filename = "temp_recording.wav"
        wf = wave.open(wav_filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        return wav_filename


    def transcribe(self, filename):
        with open(filename, "rb") as audio_file:
            transcription_result = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcription_result.text

    def record_and_transcribe(self):
        wav_file = self.record_until_silent()
        text = self.transcribe(wav_file)
        os.remove(wav_file)
        return text

    def listen_for_hotword(self, access_key=None, keywords=None, sensitivities=None):
        """
        Listens for a predefined hotword using Porcupine.
        Returns the index of the detected keyword, or None if interrupted.
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
            frames_per_buffer=self._porcupine.frame_length
        )
        self._stream = stream
        print(f"[Hotword] Listening for hotword(s): {keywords}")
        try:
            while True:
                pcm = stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                pcm_unpacked = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
                keyword_index = self._porcupine.process(pcm_unpacked)
                if keyword_index >= 0:
                    print(f"[Hotword] Detected: {keywords[keyword_index]}")
                    return keyword_index
                #once every 10 seconds, print a status update
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
            return ""
        text = self.transcribe(wav_file)
        os.remove(wav_file)
        return text

    def cleanup(self):
        """
        Cleanup any open audio streams, PyAudio instances, and Porcupine resources.
        """
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

if __name__ == "__main__":
    print("Starting SpeechToTextEngine test. Speak into your microphone...")
    stt_engine = SpeechToTextEngine()
    try:
        result = stt_engine.record_and_transcribe()
        print(f"Transcribed text: {result}")
    except Exception as e:
        print(f"Error during STT test: {e}")