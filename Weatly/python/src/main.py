# =================== Imports: Standard Libraries ===================
import os
import logging

# =================== Imports: Third-Party Libraries ===================
# Removed unused and commented-out imports for clarity.
import yaml
import pyaudio
import openai
from playsound import playsound
from colorama import init, Fore, Style

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    print("RPi.GPIO module not found; GPIO functionality will be disabled.")

# =================== Imports: Local Modules ===================
from hardware.arduino_interface import ArduinoInterface  # NEW import
from assistant.assistant import ConversationManager
from llm.llm_client import GPTClient, Functions
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

# NEW: Initialize assistant components
def initialize_assistant(config):
    stt_enabled = config["stt"]["enabled"]
    tts_enabled = config["tts"]["enabled"]
    assistant_config = config.get("app", {})
    max_memory = assistant_config.get("max_memory", 10)
    llm_config = config.get("llm", {})
    gpt_model = llm_config.get("model", "gpt-4o-mini")
    
    manager = ConversationManager(max_memory=max_memory)
    gpt_client = GPTClient(model=gpt_model)
    stt_engine = SpeechToTextEngine()
    tts_engine = TextToSpeechEngine()
    arduino_interface = ArduinoInterface(port="COM_DRY", dry_run=True)
    
    return manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled

# NEW: Conversation loop handling
def conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled):
    RESET = "\033[0m"
    RETRO_COLOR = "\033[95m"
    SEPARATOR = f"\n{RETRO_COLOR}" + "=" * 50 + f"{RESET}\n"
    
    function_call_count = 0
    functions_instance = Functions()  # Instantiate once with new changes
    
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
        
        # Chain workflow execution until an empty workflow is returned or max chain reached
        chain_retry = 0
        while chain_retry < 3:
            workflow = gpt_client.get_workflow(manager.get_conversation())
            #pretty print workflow with names and args
            if workflow:
              for call in workflow:
                print(f"{RETRO_COLOR}Name: {call.get('name', 'unknown')}{RESET}")
                print(f"{RETRO_COLOR}Arguments: {call.get('arguments', {})}{RESET}")
                #print(f"{RETRO_COLOR}Workflow: {workflow}{RESET}")
            if not workflow:
                print("No further research needed. Ending chain.")
                break
            fn_results = functions_instance.execute_workflow(workflow) or []
            for fn_name, result in fn_results:
                function_call_count += 1
                manager.add_text_to_conversation("system", str(result))
            # Exit chain if the workflow is now empty
            if not gpt_client.get_workflow(manager.get_conversation()):
                print("Workflow is empty after execution. Ending chain.")
                break
            chain_retry += 1

        try:
            gpt_text = gpt_client.get_text(manager.get_conversation())
        except Exception as e:
            print(f"Error getting GPT text: {e}")
            continue
        
        manager.add_text_to_conversation("assistant", gpt_text)
        manager.print_memory()

        animation = gpt_client.reply_with_animation(manager.get_conversation())
        arduino_interface.set_animation(animation)
        
        if tts_enabled:
            tts_engine.generate_and_play_advanced(gpt_text)
        else:
            print("Assistant:", gpt_text)

# =================== Main Code ===================
def main():
    config = load_config()
    openai.api_key = config["secrets"]["openai_api_key"]
    manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled = initialize_assistant(config)
    
    print_welcome()
    
    # Get initial GPT response
    manager.add_text_to_conversation("user", "Hello, please introduce yourself.")
    gpt_text = gpt_client.get_text(manager.get_conversation())
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    
    animation = gpt_client.reply_with_animation(manager.get_conversation())
    arduino_interface.set_animation(animation)  # Set initial animation
    
    if tts_enabled:
        tts_engine.generate_and_play_advanced(gpt_text)
    else:
        print("Assistant:", gpt_text)
    
    # Start the conversation loop
    conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled)
    logging.info("Assistant finished.")

if __name__ == "__main__":
    main()