# =================== Imports: Standard Libraries ===================
import os
import time
from datetime import datetime, timezone
import textwrap
import logging
import base64

# =================== Imports: Third-Party Libraries ===================
import requests
import yaml
import matplotlib.pyplot as plt
import numpy as np
import pyaudio
import openai
from openai import AzureOpenAI, OpenAI
from playsound import playsound
from colorama import init, Fore, Style

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    print("RPi.GPIO module not found; GPIO functionality will be disabled.")

import serial
import wave
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings, play

# =================== Imports: Local Modules ===================
from hardware.arduino_interface import ArduinoInterface  # NEW import
from assistant.assistant import ConversationManager
from llm.llm_client import GPTClient
from tts.tts_engine import TextToSpeechEngine  # NEW import
from stt.stt_engine import SpeechToTextEngine  # NEW import

# =================== Global Constants ===================
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
THRESHOLD = 3000
SILENCE_LIMIT = 1  # seconds

# Initialize colorama
init(autoreset=True)

# =================== Helper Functions ===================
def check_prerequisites():
    # Check if essential configuration and secret values are set
    if not openai.api_key:
        logging.error("Prerequisite check failed: OpenAI API key not set!")
        return False
    # ...additional prerequisite checks...
    logging.info("All prerequisites satisfied.")
    return True

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def init_hardware(use_raspberry):
    # Use the new ArduinoInterface.create() method
    arduino_iface = ArduinoInterface.create(use_raspberry, port='/dev/ttyACM0', baud_rate=9600)
    if use_raspberry and arduino_iface and arduino_iface.is_connected():
        time.sleep(2)
        arduino_iface.send_command("ON")
        time.sleep(3)
        arduino_iface.send_command("OFF")
        print("Hardware initialized via ArduinoInterface")
    return arduino_iface

def print_welcome():
    RESET = "\033[0m"
    RETRO_COLOR = "\033[95m"
    print(r"""
⠀⠀⡀⠀⠀⠀⣀⣠⣤⣤⣤⣤⣤⣤⣤⣤⣤⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠘⢿⣝⠛⠋⠉⠉⠉⣉⠩⠍⠉⣿⠿⡭⠉⠛⠃⠲⣞⣉⡙⠿⣇⠀⠀⠀
⠀⠀⠈⠻⣷⣄⡠⢶⡟⢁⣀⢠⣴⡏⣀⡀⠀⠀⣠⡾⠋⢉⣈⣸⣿⡀⠀⠀
⠀⠀⠀⠀⠙⠋⣼⣿⡜⠃⠉⠀⡎⠉⠉⢺⢱⢢⣿⠃⠘⠈⠛⢹⣿⡇⠀⠀
⠀⠀⠀⢀⡞⣠⡟⠁⠀⠀⣀⡰⣀⠀⠀⡸⠀⠑⢵⡄⠀⠀⠀⠀⠉⠀⣧⡀
⠀⠀⠀⠌⣰⠃⠁⣠⣖⣡⣄⣀⣀⣈⣑⣔⠂⠀⠠⣿⡄⠀⠀⠀⠀⠠⣾⣷
⠀⠀⢸⢠⡇⠀⣰⣿⣿⡿⣡⡾⠿⣿⣿⣜⣇⠀⠀⠘⣿⠀⠀⠀⠀⢸⡀⢸
⠀⠀⡆⢸⡀⠀⣿⣿⡇⣾⡿⠁⠀⠀⣹⣿⢸⠀⠀⠀⣿⡆⠀⠀⠀⣸⣤⣼
⠀⠀⢳⢸⡧⢦⢿⣿⡏⣿⣿⣦⣀⣴⣻⡿⣱⠀⠀⠀⣻⠁⠀⠀⠀⢹⠛⢻
⠀⠀⠈⡄⢷⠘⠞⢿⠻⠶⠾⠿⣿⣿⣭⡾⠃⠀⠀⢀⡟⠀⠀⠀⠀⣹⠀⡆
⠀⠀⠀⠰⣘⢧⣀⠀⠙⠢⢤⠠⠤⠄⠊⠀⠀⠀⣠⠟⠀⠀⠀⠀⠀⢧⣿⠃
⠀⣀⣤⣿⣇⠻⣟⣄⡀⠀⠘⣤⣣⠀⠀⠀⣀⢼⠟⠀⠀⠀⠀⠀⠄⣿⠟⠀
⠿⠏⠭⠟⣤⣴⣬⣨⠙⠲⢦⣧⡤⣔⠲⠝⠚⣷⠀⠀⠀⢀⣴⣷⡠⠃⠀⠀
⠀⠀⠀⠀⠀⠉⠉⠉⠛⠻⢛⣿⣶⣶⡽⢤⡄⢛⢃⣒⢠⣿⣿⠟⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠉⠉⠉⠁⠀⠁⠀⠀⠀⠀⠀
    """)
    print(f"{RETRO_COLOR}Welcome to the AI Assistant!{RESET}")

# =================== Main Code ===================
def main():
    # ---- Initialization Section ----
    init(autoreset=True)
    plt.ion()

    # ---- Configuration Loading Section ----
    config = load_config()
    openai.api_key = config["secrets"]["openai_api_key"]
    subscription_key = config["secrets"].get("openai_api_key", "")
    APPINSIGHTS_IKEY = config["secrets"]["appinsights_ikey"]
    client = ElevenLabs(api_key=config["secrets"]["elevenlabs_api_key"])
    use_raspberry = config.get("use_raspberry", True)
    stt_enabled = config["stt"]["enabled"]
    tts_enabled = config["tts"]["enabled"]

    if not check_prerequisites():
        print("Missing prerequisites. Please check configuration.")
        return

    # ---- Hardware Initialization Section ----
    arduino_iface = init_hardware(use_raspberry)
        
    # ---- Assistant & Client Initialization Section ----
    manager = ConversationManager(max_memory=10)
    gpt_client = GPTClient(api_key=subscription_key)
    stt_engine = SpeechToTextEngine()
    tts_engine = TextToSpeechEngine()
    
    print_welcome()
    # Get initial GPT response
    gpt_text = gpt_client.get_text(manager.get_conversation())
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    
    if tts_enabled:
        tts_engine.generate_and_play_advanced(gpt_text)
    else:
        print("Assistant:", gpt_text)
    
    # ---- Conversation Loop Section ----
    RESET = "\033[0m"
    RETRO_COLOR = "\033[95m"
    SEPARATOR = f"\n{RETRO_COLOR}" + "=" * 50 + f"{RESET}\n"
    while True:
        print(SEPARATOR)
        if stt_enabled:
            user_input = stt_engine.record_and_transcribe()
            print("User (via STT):", user_input)
        else:
            user_input = input("User: ")
        if user_input.lower() == "exit":
            break
        manager.add_text_to_conversation("user", user_input)
        
        start_gpt = time.perf_counter()
        try:
            gpt_text = gpt_client.get_text(manager.get_conversation())
        except Exception as e:
            print(f"Error getting GPT text: {e}")
            continue
        end_gpt = time.perf_counter()
        # ...existing code: calculate time_gpt if needed...
        
        manager.add_text_to_conversation("assistant", gpt_text)
        manager.print_memory()
        
        if tts_enabled:
            tts_engine.generate_and_play_advanced(gpt_text)
        else:
            print("Assistant:", gpt_text)
    
    logging.info("Assistant finished.")

if __name__ == "__main__":
    main()