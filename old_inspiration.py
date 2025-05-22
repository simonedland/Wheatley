import os
import time
import json
import textwrap
from datetime import datetime, timezone
import requests
from playsound import playsound
import openai
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Google Calendar API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Additional imports for voice recording, Arduino commands, and hotword detection
import pyaudio
import numpy as np
import wave
import serial
import struct
import pvporcupine

from colorama import init

# -----------------------------------------------------------------------------
# Timer utility 
# -----------------------------------------------------------------------------
class Timer:
    def __init__(self, label=""):
        self.label = label
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.elapsed = self.end - self.start

# -----------------------------------------------------------------------------
# Voice Recording Functions 
# -----------------------------------------------------------------------------
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
THRESHOLD = 3000
SILENCE_LIMIT = 2

def record_until_silent():
    print("listening...")
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, frames_per_buffer=CHUNK, input_device_index=1)
    frames = []
    silent_frames = 0
    recording = False
    start_time = time.time()
    silent = True
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        data_int = np.frombuffer(data, dtype=np.int16)
        amplitude = np.max(np.abs(data_int))
        if amplitude > THRESHOLD:
            if not recording:
                recording = True
            frames.append(data)
            silent_frames = 0
            if silent:
                print("Recording...")
            silent = False
        else:
            if time.time() - start_time > 10 and silent:
                return ""
            if recording:
                silent_frames += 1
                frames.append(data)
                if silent_frames > (RATE / CHUNK * SILENCE_LIMIT):
                    break
    stream.stop_stream()
    stream.close()
    audio.terminate()
    wav_filename = "temp_recording.wav"
    wf = wave.open(wav_filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b"".join(frames))
    wf.close()
    return wav_filename

def get_voice_input():
    wav_file = record_until_silent()
    if not wav_file:
        print("No audio detected.")
        return ""
    with open(wav_file, "rb") as f:
        transcription = openai.Audio.transcribe("whisper-1", f)
        text = transcription["text"]
    os.remove(wav_file)
    return text

# -----------------------------------------------------------------------------
# Hotword Detection using Porcupine 
# -----------------------------------------------------------------------------
def listen_for_hotword():
    """
    Listens for a predefined hotword using Porcupine.
    Once detected, the function returns to allow further processing.
    """
    access_key = pvporcupine_api_key
    print(access_key)
    porcupine = pvporcupine.create(
        access_key=access_key,
        keywords=["computer", "jarvis"], sensitivities=[0.5, 0.5]
    )
    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )
    print("Listening for hotword...")
    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
            keyword_index = porcupine.process(pcm_unpacked)
            if keyword_index >= 0:
                print("Hotword Detected!")
                break
    except KeyboardInterrupt:
        print("Keyword detection interrupted.")
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()