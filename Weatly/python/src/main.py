import os
import time
from datetime import datetime, timezone
import textwrap
import logging
import requests
import openai
import matplotlib.pyplot as plt
import yaml
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    print("RPi.GPIO module not found; GPIO functionality will be disabled.")
import serial
import wave
from colorama import init, Fore, Style
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings, play
import numpy as np
import pyaudio
from openai import OpenAI
import base64
from openai import AzureOpenAI
from playsound import playsound
from hardware.arduino_interface import ArduinoInterface  # NEW import

def check_prerequisites():
    # Check if essential configuration and secret values are set
    if not openai.api_key:
        logging.error("Prerequisite check failed: OpenAI API key not set!")
        return False
    # ... add additional prerequisite checks as needed ...
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
        print("hello world")
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

# Load configuration from config folder
config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)
use_raspberry = config.get("use_raspberry", True)  # New flag to switch Raspberry-specific code

# Set secrets from config
openai.api_key = config["secrets"]["openai_api_key"]
# Add subscription key from config
subscription_key = config["secrets"].get("openai_api_key", "")

# Configure ElevenLabs client using our utils module (overwrite client api key)
APPINSIGHTS_IKEY = config["secrets"]["appinsights_ikey"]
# Initialize ElevenLabs client using the API key from config secrets
client = ElevenLabs(api_key=config["secrets"]["elevenlabs_api_key"])

# ...existing code for Timer, rate_limit, etc. are now moved to utils modules ...
from utils.rate_limit import rate_limit
from assistant import ConversationManager, Assistant

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
THRESHOLD = 3000
SILENCE_LIMIT = 1  # seconds

init(autoreset=True)

from llm.llm_client import GPTClient
from tts.tts_engine import TextToSpeechEngine  # NEW import
from stt.stt_engine import SpeechToTextEngine  # NEW import

class ConversationManager:
    """
    Manages the conversation history with a fixed memory.
    """
    def __init__(self, max_memory=5):
        self.max_memory = max_memory
        self.messages = [{
            "role": "system",
            "content": (
                "you are Weatly, a helpful assistant. from portal 2.0, answer in a single short sentence"
            )
        }]

    def add_text_to_conversation(self, role, text):
        self.messages.append({"role": role, "content": text})
        # Keep only the latest max_memory messages (excluding system)
        while len(self.messages) > self.max_memory + 1:
            self.messages.pop(1)

    def get_conversation(self):
        return self.messages

    def print_memory(self):
        debug_color = "\033[94m"      # system
        user_color = "\033[92m"       # user
        assistant_color = "\033[93m"  # assistant
        reset_color = "\033[0m"
        max_width = 70
        
        print(f"\n{debug_color}+------------------------ Conversation Memory ------------------------+{reset_color}")
        for idx, msg in enumerate(self.messages):
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                role_color = debug_color; prefix = f"[{idx}] {role}: "
            elif role == "user":
                role_color = user_color; prefix = f"[{idx}] {role}:      "
            elif role == "assistant":
                role_color = assistant_color; prefix = f"[{idx}] {role}: "
            else:
                role_color = debug_color; prefix = f"[{idx}] {role}: "
            wrapped = textwrap.wrap(content, width=max_width-len(prefix))
            if wrapped:
                print(f"{role_color}{prefix}{wrapped[0]}{reset_color}")
                for line in wrapped[1:]:
                    print(f"{role_color}{' ' * len(prefix)}{line}{reset_color}")
            else:
                print(f"{role_color}{prefix}{reset_color}")
        print(f"{debug_color}+---------------------------------------------------------------------+{reset_color}\n")

# Retrieve STT/TTS switches from config
stt_enabled = config["stt"]["enabled"]
tts_enabled = config["tts"]["enabled"]

def main():
    init(autoreset=True)
    plt.ion()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    if not check_prerequisites():
        print("Missing prerequisites. Please check configuration.")
        return

    config = load_config()
    use_raspberry = config.get("use_raspberry", True)
    openai.api_key = config["secrets"]["openai_api_key"]
    subscription_key = config["secrets"].get("openai_api_key", "")
    client = ElevenLabs(api_key=config["secrets"]["elevenlabs_api_key"])
    
    # Initialize hardware via ArduinoInterface
    arduino_iface = init_hardware(use_raspberry)
    stt_enabled = config["stt"]["enabled"]
    tts_enabled = config["tts"]["enabled"]
    
    # Initialize conversation and clients
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
    
    RESET = "\033[0m"
    RETRO_COLOR = "\033[95m"
    SEPARATOR = f"\n{RETRO_COLOR}" + "="*50 + f"{RESET}\n"
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
        time_gpt = end_gpt - start_gpt
        
        manager.add_text_to_conversation("assistant", gpt_text)
        manager.print_memory()
        
        if tts_enabled:
            tts_engine.generate_and_play_advanced(gpt_text)
        else:
            print("Assistant:", gpt_text)
    
    logging.info("Assistant finished.")

if __name__ == "__main__":
    main()