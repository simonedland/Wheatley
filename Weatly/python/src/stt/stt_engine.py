import os
import wave
import numpy as np
import pyaudio
import openai
import yaml

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

    def dry_run(self, filename):
        # Recognize speech using Whisper model deployed in Azure (dry run)
        # TODO: Replace the following with the actual call to Azure's deployed Whisper service
        return "Dry run: recognized text from Whisper model on Azure (simulated)"

    def record_until_silent(self):
        """Record audio until silence is detected."""
        audio = pyaudio.PyAudio()
        try:
            stream = audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK, input_device_index=2)
        except:
            stream = audio.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK, input_device_index=1)
        frames = []
        silent_frames = 0
        recording = False
        print("Monitoring...")

        min_amplitude = float('inf')
        max_amplitude = float('-inf')

        while True:
            data = stream.read(self.CHUNK, exception_on_overflow = False)
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

        stream.stop_stream()
        stream.close()
        audio.terminate()
        wav_filename = "temp_recording.wav"
        wf = wave.open(wav_filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(audio.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        return wav_filename


    def transcribe(self, filename):
        with open(filename, "rb") as audio_file:
            transcription_result = openai.Audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcription_result.text

    def record_and_transcribe(self):
        wav_file = self.record_until_silent()
        text = self.transcribe(wav_file)
        os.remove(wav_file)
        return text