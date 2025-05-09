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
# Global Weather Code Descriptions (WMO Weather interpretation codes)
# -----------------------------------------------------------------------------
WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear, partly cloudy, and overcast",
    2: "Mainly clear, partly cloudy, and overcast",
    3: "Mainly clear, partly cloudy, and overcast",
    45: "Fog and depositing rime fog",
    48: "Fog and depositing rime fog",
    51: "Drizzle: Light intensity",
    53: "Drizzle: Moderate intensity",
    55: "Drizzle: Dense intensity",
    56: "Freezing Drizzle: Light intensity",
    57: "Freezing Drizzle: Dense intensity",
    61: "Rain: Slight intensity",
    63: "Rain: Moderate intensity",
    65: "Rain: Heavy intensity",
    66: "Freezing Rain: Light intensity",
    67: "Freezing Rain: Heavy intensity",
    71: "Snow fall: Slight intensity",
    73: "Snow fall: Moderate intensity",
    75: "Snow fall: Heavy intensity",
    77: "Snow grains",
    80: "Rain showers: Slight intensity",
    81: "Rain showers: Moderate intensity",
    82: "Rain showers: Violent",
    85: "Snow showers: Slight intensity",
    86: "Snow showers: Heavy intensity",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail (Central Europe only)",
    99: "Thunderstorm with heavy hail (Central Europe only)"
}

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

# -----------------------------------------------------------------------------
# Sample Function for Function Calling: get_weather 
# -----------------------------------------------------------------------------
def get_weather(
    lat,
    lon,
    include_forecast=False,
    forecast_days=7,
    extra_hourly=["temperature_2m", "weathercode"],
    temperature_unit="celsius",
    wind_speed_unit="kmh"
):
    base_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&current_weather=true"
        f"&forecast_days={forecast_days}"
        f"&temperature_unit={temperature_unit}"
        f"&wind_speed_unit={wind_speed_unit}"
    )
    if include_forecast and extra_hourly:
        hourly_params = ",".join(extra_hourly)
        base_url += f"&hourly={hourly_params}"
    try:
        response = requests.get(base_url)
        data = response.json()
        cw = data.get("current_weather", {})
        summary = (
            f"Weather Details:\n"
            f"Location: ({data.get('latitude')}, {data.get('longitude')})\n"
            f"Temperature: {cw.get('temperature')}°C\n"
            f"Time: {cw.get('time')}\n"
            f"Elevation: {data.get('elevation')} m\n"
            f"Timezone: {data.get('timezone')} ({data.get('timezone_abbreviation')})"
        )
        # Interpret the current weather code.
        weather_code = cw.get("weathercode")
        if weather_code is not None:
            try:
                weather_code_int = int(weather_code)
            except Exception:
                weather_code_int = None
            if weather_code_int is not None:
                description = WEATHER_CODE_DESCRIPTIONS.get(weather_code_int, "Unknown weather condition")
                summary += f"\nWeather Condition: {description} (Code: {weather_code_int})"
        # Process extended forecast if requested.
        if include_forecast and extra_hourly:
            hours_data = data.get("hourly", {})
            times = hours_data.get("time", [])
            forecast_summary = "\nExtended Forecast:\n"
            for i, t in enumerate(times):
                line_info = [t]
                for var_name in extra_hourly:
                    var_values = hours_data.get(var_name, [])
                    if i < len(var_values):
                        value = var_values[i]
                        # If the variable is weathercode, interpret it.
                        if var_name == "weathercode":
                            try:
                                code_int = int(value)
                                desc = WEATHER_CODE_DESCRIPTIONS.get(code_int, "Unknown")
                                line_info.append(f"{var_name}={value} ({desc})")
                            except Exception:
                                line_info.append(f"{var_name}={value}")
                        else:
                            line_info.append(f"{var_name}={value}")
                forecast_summary += ", ".join(line_info) + "\n"
            summary += forecast_summary
        return summary
    except Exception as e:
        return f"Error retrieving weather: {e}"

