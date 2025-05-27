# =================== Imports: Standard Libraries ===================
import os  # For file and path operations
import logging  # For logging events and timings
import time  # For timing actions
import asyncio
import datetime
from dataclasses import dataclass
from typing import Dict, Any, Optional

# =================== Imports: Third-Party Libraries ===================
import yaml  # For reading YAML config files
import pyaudio  # For audio input/output
import openai  # For OpenAI API access
from playsound import playsound  # For playing audio files
from colorama import init, Fore, Style  # For colored terminal output

# Try to import RPi.GPIO for Raspberry Pi GPIO control; disable if not available
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    print("RPi.GPIO module not found; GPIO functionality will be disabled.")

# =================== Imports: Local Modules ===================
from hardware.arduino_interface import ArduinoInterface  # Arduino hardware interface
from assistant.assistant import ConversationManager  # Manages conversation history
from llm.llm_client import GPTClient, Functions  # LLM client and function tools
from tts.tts_engine import TextToSpeechEngine  # Text-to-speech engine
from stt.stt_engine import SpeechToTextEngine  # Speech-to-text engine

# =================== Global Constants ===================
CHUNK = 1024  # Audio chunk size
FORMAT = pyaudio.paInt16  # Audio format
CHANNELS = 1  # Mono audio
RATE = 44100  # Audio sample rate
THRESHOLD = 3000  # Audio threshold for silence detection
SILENCE_LIMIT = 1  # Silence limit in seconds

# Initialize colorama for colored terminal output
init(autoreset=True)

# =================== Helper Functions ===================

# Robust logging setup: always log to file only
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove all handlers associated with the root logger object (prevents duplicate logs)
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

file_handler = logging.FileHandler('assistant.log', mode='w', encoding='utf-8')
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

# Suppress verbose HTTP logs from openai, httpx, and requests
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# Load configuration from YAML file
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

# Print ASCII art welcome message to the terminal
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

# =================== Assistant Initialization ===================
# Set up all assistant components (LLM, TTS, STT, Arduino, etc.)
def initialize_assistant(config):
    start_time = time.time()  # Start timing initialization
    stt_enabled = config["stt"]["enabled"]  # Speech-to-text enabled
    tts_enabled = config["tts"]["enabled"]  # Text-to-speech enabled
    assistant_config = config.get("app")  # App-specific config
    max_memory = assistant_config.get("max_memory")  # Conversation memory size
    llm_config = config.get("llm")  # LLM config
    gpt_model = llm_config.get("model")  # LLM model name
    
    # Initialize core components
    manager = ConversationManager(max_memory=max_memory)
    gpt_client = GPTClient(model=gpt_model)
    stt_engine = SpeechToTextEngine()
    tts_engine = TextToSpeechEngine()
    import sys
    port = None
    dry_run = False
    # Detect available serial ports for Arduino (platform-specific)
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
    elapsed = time.time() - start_time
    logging.info(f"initialize_assistant completed in {elapsed:.3f} seconds.")
    # Return all initialized components and feature flags
    return manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled

# =================== Event Dataclass ===================
@dataclass
class Event:
    source: str        # e.g. "user", "timer", "gpio", "webhook", etc.
    payload: str       # human-readable description
    metadata: Optional[Dict[str, Any]] = None
    ts: datetime.datetime = datetime.datetime.utcnow()

    def __str__(self) -> str:
        meta = f" {self.metadata}" if self.metadata else ""
        return f"[{self.source.upper()}] {self.payload}{meta}"

# =================== Conversation loop handling ===================
# Main loop for user interaction, workflow execution, and response
def conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled):
    RESET = "\033[0m"
    RETRO_COLOR = "\033[95m"
    SEPARATOR = f"\n{RETRO_COLOR}" + "=" * 50 + f"{RESET}\n"

    while True:
        # --- New User Input Section ---
        action_start = time.time()
        # Get user input (via STT if enabled, else text input)
        if stt_enabled:
            user_input = stt_engine.record_and_transcribe()
        else:
            user_input = input("User: ")
        # Log the new user input and timing
        logging.info(f"\n=== New User Input: {user_input} ===")
        action_start = time.time()
        manager.add_text_to_conversation("user", user_input)
        
        # Exit if user types 'exit'
        if user_input.lower() == "exit":
            break
        
        # --- Workflow/Function Execution Section ---
        chain_retry = 0
        while chain_retry < 3:
            action_start = time.time()
            # Get workflow (function/tool calls) from GPT based on conversation
            workflow = gpt_client.get_workflow(manager.get_conversation())
            logging.info(f"GPT workflow generation took {time.time() - action_start:.3f} seconds.")
            if workflow:
                # Log each function call in the workflow
                for call in workflow:
                    print(f"{RETRO_COLOR}Name: {call.get('name', 'unknown')}{RESET}")
                    print(f"{RETRO_COLOR}Arguments: {call.get('arguments', {})}{RESET}")
                # If the workflow includes web_search_call_result items, add their text as system context
                for item in workflow:
                    if item.get("name") == "web_search_call_result":
                        context_text = item.get("arguments", {}).get("text", "")
                        if context_text:
                            manager.add_text_to_conversation("system", f"Info: {context_text}")
                # Remove non-executable info items
                workflow = [item for item in workflow if item.get("name") != "web_search_call_result"]
            if not workflow:
                break
            # Execute all tools/functions in the workflow and add results to conversation
            logging.info(f"--- Executing Tool Workflow ---")
            fn_results = Functions().execute_workflow(workflow) or []
            for fn_name, result in fn_results:
                manager.add_text_to_conversation("system", str(result))
            chain_retry += 1

        # --- Assistant Response Section ---
        try:
            action_start = time.time()
            # Get assistant's text response from GPT
            gpt_text = gpt_client.get_text(manager.get_conversation())
            logging.info(f"GPT text response in {time.time() - action_start:.3f} seconds.")
        except Exception as e:
            logging.error(f"Error getting GPT text: {e}")
            continue
        
        # Add assistant response to conversation and print memory (for debugging)
        manager.add_text_to_conversation("assistant", gpt_text)
        manager.print_memory()
        
        # --- Animation/Servo Section ---
        action_start = time.time()
        # Get animation from GPT and update Arduino/servo
        animation = gpt_client.reply_with_animation(manager.get_conversation())
        arduino_interface.set_animation(animation)
        arduino_interface.servo_controller.print_servo_status()
        logging.info(f"Animation and servo status in {time.time() - action_start:.3f} seconds.")
        
        # --- TTS/Output Section ---
        action_start = time.time()
        # Speak or log the assistant's response
        if tts_enabled:
            tts_engine.generate_and_play_advanced(gpt_text)
        else:
            logging.info(f"Assistant: {gpt_text}")
        logging.info(f"TTS or print response in {time.time() - action_start:.3f} seconds.")
        logging.info("\n" + "=" * 60 + "\n")

# =================== Async Event Handling ===================
async def user_input_producer(q: asyncio.Queue):
    loop = asyncio.get_event_loop()
    while True:
        text = await loop.run_in_executor(None, input, "You: ")
        await q.put(Event("user", text.strip()))
        if text.strip().lower() == "exit":
            break

def print_event(event: Event):
    print(event)

async def async_conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled):
    queue: asyncio.Queue = asyncio.Queue()
    # Start event producers
    asyncio.create_task(user_input_producer(queue))
    print("🤖 Assistant running. Type 'exit' to quit.\n")
    while True:
        event: Event = await queue.get()
        print_event(event)
        if event.source == "user":
            manager.add_text_to_conversation("user", event.payload)
            if event.payload.lower() == "exit":
                break
        else:
            # If this is a timer event, make the system message more explicit
            if event.source == "timer":
                timer_label = event.payload if hasattr(event, 'payload') else "Timer"
                timer_duration = None
                if hasattr(event, 'metadata') and event.metadata:
                    timer_duration = event.metadata.get("duration")
                timer_msg = f"TIMER for {timer_duration} sec UP: {timer_label}" if timer_duration else f"TIMER UP: {timer_label}"
                manager.add_text_to_conversation("system", timer_msg)
            else:
                manager.add_text_to_conversation("system", str(event))
        # --- TOOL/WORKFLOW SECTION ---
        chain_retry = 0
        while chain_retry < 3:
            try:
                workflow = gpt_client.get_workflow(manager.get_conversation())
            except Exception as e:
                logging.error(f"Error getting GPT workflow: {e}")
                break
            if workflow:
                for call in workflow:
                    print(f"Tool Name: {call.get('name', 'unknown')}")
                    print(f"Arguments: {call.get('arguments', {})}")
                for item in workflow:
                    if item.get("name") == "web_search_call_result":
                        context_text = item.get("arguments", {}).get("text", "")
                        if context_text:
                            manager.add_text_to_conversation("system", f"Info: {context_text}")
                workflow = [item for item in workflow if item.get("name") != "web_search_call_result"]
            if not workflow:
                break
            try:
                fn_results = Functions().execute_workflow(workflow, event_queue=queue) or []
            except Exception as e:
                logging.error(f"Error executing workflow tools: {e}")
                break
            for fn_name, result in fn_results:
                manager.add_text_to_conversation("system", str(result))
            chain_retry += 1
        # --- ASSISTANT RESPONSE SECTION ---
        try:
            gpt_text = gpt_client.get_text(manager.get_conversation())
        except Exception as e:
            logging.error(f"Error getting GPT text: {e}")
            continue
        manager.add_text_to_conversation("assistant", gpt_text)
        manager.print_memory()
        animation = gpt_client.reply_with_animation(manager.get_conversation())
        arduino_interface.set_animation(animation)
        arduino_interface.servo_controller.print_servo_status()
        if tts_enabled:
            tts_engine.generate_and_play_advanced(gpt_text)
        else:
            print(f"Assistant: {gpt_text}")
    print("👋 Exiting…")

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

    # Initialize assistant components
    manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled = initialize_assistant(config)
    
    print_welcome()
    
    # Print the status of all servos
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
    
    # Start the async event-based conversation loop
    asyncio.run(async_conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled))
    logging.info("Assistant finished.")

if __name__ == "__main__":
    main()