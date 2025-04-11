# =================== Imports: Standard Libraries ===================
import os
import logging

# =================== Imports: Third-Party Libraries ===================
#import requests
import yaml
#import matplotlib.pyplot as plt
#import numpy as np
import pyaudio
import openai
#from openai import AzureOpenAI, OpenAI
from playsound import playsound
from colorama import init, Fore, Style

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    print("RPi.GPIO module not found; GPIO functionality will be disabled.")

#import serial
#import wave
#from elevenlabs.client import ElevenLabs
#from elevenlabs import Voice, VoiceSettings, play

# =================== Imports: Local Modules ===================
from hardware.arduino_interface import ArduinoInterface  # NEW import
from assistant.assistant import ConversationManager
from llm.llm_client import GPTClient  # NEW import
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

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

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

    # ---- Configuration Loading Section ----
    config = load_config()
    openai.api_key = config["secrets"]["openai_api_key"]
    subscription_key = config["secrets"].get("openai_api_key", "")
    stt_enabled = config["stt"]["enabled"]
    tts_enabled = config["tts"]["enabled"]

    # Use configuration for conversation memory and LLM model
    assistant_config = config.get("app", {})
    max_memory = assistant_config.get("max_memory", 10)
    llm_config = config.get("llm", {})
    gpt_model = llm_config.get("model", "gpt-4o-mini")
        
    # ---- Assistant & Client Initialization Section ----
    manager = ConversationManager(max_memory=max_memory)
    gpt_client = GPTClient(api_key=subscription_key, model=gpt_model)
    stt_engine = SpeechToTextEngine()
    tts_engine = TextToSpeechEngine()
    
    print_welcome()

    # Get initial GPT response
    gpt_text = gpt_client.get_text(manager.get_conversation())
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()

    # NEW: Setup ArduinoInterface with dry_run and override set_animation
    arduino_interface = ArduinoInterface(port="COM_DRY", dry_run=True)
    animation = gpt_client.reply_with_animation(manager.get_conversation())
    print("Initial animation:", animation)
    arduino_interface.set_animation(animation)  # Set initial animation
    
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
            print("User:", user_input)
        else:
            user_input = input("User: ")
        if user_input.lower() == "exit":
            break
        manager.add_text_to_conversation("user", user_input)
        # NEW: Invoke reply_with_animation to update the hardware animation (dry run)
        animation = gpt_client.reply_with_animation(manager.get_conversation())
        print("Updated animation:", animation)
        arduino_interface.set_animation(animation)

        try:
            gpt_text = gpt_client.get_text(manager.get_conversation())
        except Exception as e:
            print(f"Error getting GPT text: {e}")
            continue
        
        manager.add_text_to_conversation("assistant", gpt_text)
        manager.print_memory()
        
        if tts_enabled:
            tts_engine.generate_and_play_advanced(gpt_text)
        else:
            print("Assistant:", gpt_text)
    
    logging.info("Assistant finished.")

if __name__ == "__main__":
    main()