# =================== Imports: Standard Libraries ===================
import os
import logging

# =================== Imports: Third-Party Libraries ===================
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
⠀⠀⠈⠻⣷⣄⡠⢶⡟⢀⣀⢠⣴⡏⣀⡀⠀⠀⣠⡾⠋⢉⣈⣸⣿⡀⠀⠀
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
    assistant_config = config.get("app")
    max_memory = assistant_config.get("max_memory")
    llm_config = config.get("llm")
    gpt_model = llm_config.get("model")
    
    manager = ConversationManager(max_memory=max_memory)
    gpt_client = GPTClient(model=gpt_model)
    stt_engine = SpeechToTextEngine()
    tts_engine = TextToSpeechEngine()
    import sys
    port = None
    dry_run = False
    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        print("Available ports:")
        os.system("ls /dev/tty*")
        port = "/dev/ttyUSB0"
    elif sys.platform.startswith("win"):
        from serial.tools import list_ports
        ports = list(list_ports.comports())
        print("Available ports:")
        for p in ports:
            print(p.device)
        # Try to use COM7 if available, else use first available port
        port = None
        for p in ports:
            if p.device == "COM7":
                port = "COM7"
        if not port:
            print("No serial ports found. Running in dry run mode.")
            dry_run = True
    # Initialize Arduino interface with error handling
    arduino_interface = None
    if port and not dry_run:
        try:
            arduino_interface = ArduinoInterface(port=port)
            arduino_interface.connect()
        except Exception as e:
            print(f"Could not connect to Arduino on {port}: {e}. Running in dry run mode.")
            arduino_interface = ArduinoInterface(port=port, dry_run=True)
    else:
        arduino_interface = ArduinoInterface(port="dryrun", dry_run=True)
    return manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled

# NEW: Conversation loop handling
def conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled):
    # Set up terminal formatting variables
    RESET = "\033[0m"
    RETRO_COLOR = "\033[95m"
    SEPARATOR = f"\n{RETRO_COLOR}" + "=" * 50 + f"{RESET}\n"

    while True:
        print(SEPARATOR)
        # Get the user input either via Speech-to-Text (if enabled) or regular text input
        if stt_enabled:
            user_input = stt_engine.record_and_transcribe()
            print("User:", user_input)
        else:
            user_input = input("User: ")
        
        # Exit loop if user types "exit"
        if user_input.lower() == "exit":
            break
        
        # Save the user input into the conversation history
        manager.add_text_to_conversation("user", user_input)
        
        chain_retry = 0  # Initialize a loop count for function workflow processing
        while chain_retry < 3:
            # Retrieve a workflow (list of function calls) from GPT based on the conversation context
            workflow = gpt_client.get_workflow(manager.get_conversation())
            if workflow:
                # Debug: Print out the name and arguments for each function call retrieved
                for call in workflow:
                    print(f"{RETRO_COLOR}Name: {call.get('name', 'unknown')}{RESET}")
                    print(f"{RETRO_COLOR}Arguments: {call.get('arguments', {})}{RESET}")
                # If the workflow includes web_search_call_result items, add their text as system context
                for item in workflow:
                    if item.get("name") == "web_search_call_result":
                        context_text = item.get("arguments", {}).get("text", "")
                        if context_text:
                            manager.add_text_to_conversation("system", f"Info: {context_text}")
                # Remove non-executable info items from the workflow for subsequent function execution
                workflow = [item for item in workflow if item.get("name") != "web_search_call_result"]
            # Break out of retry loop if no executable workflow remains
            if not workflow:
                break
            # Execute the workflow functions and add their results to the conversation as system messages
            fn_results = Functions().execute_workflow(workflow) or []
            for fn_name, result in fn_results:
                manager.add_text_to_conversation("system", str(result))
            # If no further workflow steps are generated, exit the retry loop
            if not gpt_client.get_workflow(manager.get_conversation()):
                break
            chain_retry += 1  # Increment retry counter if additional workflow steps were generated

        try:
            # Retrieve the assistant's text response from GPT using the current conversation history
            gpt_text = gpt_client.get_text(manager.get_conversation())
        except Exception as e:
            print(f"Error getting GPT text: {e}")
            continue
        
        # Add the assistant's GPT response to the conversation history and display the conversation memory
        manager.add_text_to_conversation("assistant", gpt_text)
        manager.print_memory()
        
        # Set and activate the assistant's animation based on the GPT response
        animation = gpt_client.reply_with_animation(manager.get_conversation())
        arduino_interface.set_animation(animation)
        arduino_interface.servo_controller.print_servo_status()
        
        # If TTS is enabled, use it to vocalize the response; otherwise, print the text response
        if tts_enabled:
            tts_engine.generate_and_play_advanced(gpt_text)
        else:
            print("Assistant:", gpt_text)

# =================== Main Code ===================
def main():
    config = load_config()
    openai.api_key = config["secrets"]["openai_api_key"]

    # Print active/inactive features from config
    stt_enabled = config["stt"]["enabled"]
    tts_enabled = config["tts"]["enabled"]
    feature_summary = "\nFeature Status:\n"
    feature_summary += f" - Speech-to-Text (STT): {'Active' if stt_enabled else 'Inactive'}\n"
    feature_summary += f" - Text-to-Speech (TTS): {'Active' if tts_enabled else 'Inactive'}\n"
    print(feature_summary)

    # NEW: Initialize assistant components
    manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled = initialize_assistant(config)
    
    print_welcome()
    
    # NEW: Print the status of all servos
    arduino_interface.set_animation("neutral")  # Set initial animation to neutral
    arduino_interface.servo_controller.print_servo_status()
    
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