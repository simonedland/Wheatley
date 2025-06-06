# =================== Imports: Standard Libraries ===================
import os  # For file and path operations
import logging  # For logging events and timings
import time  # For timing actions
import asyncio
import datetime
from dataclasses import dataclass
from typing import Dict, Any, Optional
import sys

# =================== Imports: Third-Party Libraries ===================
import yaml  # For reading YAML config files
import pyaudio  # For audio input/output
import openai  # For OpenAI API access
from playsound import playsound  # For playing audio files
from colorama import init, Fore, Style  # For colored terminal output
import pathlib
import struct
import pvporcupine

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
        port = "/dev/ttyACM0"
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

# =================== Async Event Handling ===================
async def user_input_producer(q: asyncio.Queue):
    loop = asyncio.get_event_loop()
    while True:
        text = await loop.run_in_executor(None, input, "You: ")
        await q.put(Event("user", text.strip(), {"input_type": "text"}))
        if text.strip().lower() == "exit":
            break

def print_event(event: Event):
    print(event)

async def hotword_listener(queue, stt_engine):
    """Background task using streaming STT triggered by a hotword."""
    print("[Hotword] Background listener started.")
    loop = asyncio.get_event_loop()
    try:
        while True:
            if stt_engine.is_paused():
                await asyncio.sleep(0.1)
                continue
            # Run the blocking live voice input workflow in a thread
            text = await loop.run_in_executor(
                None, stt_engine.get_live_voice_input_blocking
            )
            if text and text.strip():
                await queue.put(
                    Event("user", text.strip(), {"input_type": "voice"})
                )
    except asyncio.CancelledError:
        print("[Hotword] Listener cancelled.")
    except Exception as e:
        print(f"[Hotword] Listener error: {e}")

async def async_conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled):
    import sys
    queue: asyncio.Queue = asyncio.Queue()
    # Start both input producers as background tasks and keep references
    user_task = asyncio.create_task(user_input_producer(queue))  # Text input
    hotword_task = None
    if stt_enabled:
        hotword_task = asyncio.create_task(hotword_listener(queue, stt_engine))  # Voice input
    last_input_type = "text"
    print("🤖 Assistant running. Type 'exit' to quit. Type or say hotword to speak.\n")
    try:
        while True:
            event: Event = await queue.get()
            print_event(event)
            if event.source == "user":
                if event.metadata:
                    last_input_type = event.metadata.get("input_type", "text")
                else:
                    last_input_type = "text"
                manager.add_text_to_conversation("user", event.payload)
                if event.payload.lower() == "exit":
                    # Cancel background tasks
                    user_task.cancel()
                    if hotword_task:
                        hotword_task.cancel()
                    break
            else:
                # If this is a timer event, make the system message more explicit
                if event.source == "timer":
                    timer_label = event.payload if hasattr(event, 'payload') else "Timer"
                    if hasattr(event, 'metadata') and event.metadata:
                        timer_duration = event.metadata.get("duration")
                    timer_msg = f"TIMER labeled {timer_label} for {timer_duration} is up inform the user." if timer_duration else f"TIMER UP: {timer_label}"
                    manager.add_text_to_conversation("system", timer_msg)

                elif event.source == "reminder":
                    reminder_text = event.payload if hasattr(event, 'payload') else "Reminder"
                    manager.add_text_to_conversation("system", f"Reminder has triggered with the following text: {reminder_text}")

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

            # --- ANIMATION SECTION ---
            animation = gpt_client.reply_with_animation(manager.get_conversation())
            print(f"[Animation chosen]: {animation}")
            arduino_interface.set_animation(animation)
            
            # Print currently scheduled async events (timers, etc.)
            print_async_tasks()
            arduino_interface.servo_controller.print_servo_status()
            # Print assistant output and clear input prompt
            print(Fore.GREEN + Style.BRIGHT + f"\nAssistant: {gpt_text}" + Style.RESET_ALL)
            print(Fore.LIGHTBLACK_EX + Style.BRIGHT + "\n»»» Ready for your input! Type below..." + Style.RESET_ALL)
            if tts_enabled:
                # Pause hotword listener while TTS is playing
                if hotword_task:
                    hotword_task.cancel()
                    await asyncio.gather(hotword_task, return_exceptions=True)
                    hotword_task = None
                stt_engine.pause_listening()
                print("[STT] Hotword listener paused.")

                tts_engine.generate_and_play_advanced(gpt_text)

                if stt_enabled:
                    stt_engine.resume_listening()

                if stt_enabled and last_input_type == "voice":
                    print("[STT] Listening for follow-up without hotword for 10 seconds...")
                    loop = asyncio.get_event_loop()
                    follow_up = await loop.run_in_executor(
                        None,
                        lambda: stt_engine.get_live_voice_input_blocking(10, True, False)
                    )
                    if follow_up and follow_up.strip():
                        await queue.put(
                            Event("user", follow_up.strip(), {"input_type": "voice"})
                        )

                if stt_enabled:
                    hotword_task = asyncio.create_task(hotword_listener(queue, stt_engine))
                    print("[STT] Hotword listener resumed.")
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n[Main] KeyboardInterrupt or CancelledError received. Exiting...")
    finally:
        # --- CLEANUP SECTION ---
        print("[Shutdown] Cleaning up resources...")
        # Cancel any remaining tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for t in tasks:
            t.cancel()
        # Await their cancellation
        await asyncio.gather(*tasks, return_exceptions=True)
        # Cleanup STT engine if it has a cleanup method
        if hasattr(stt_engine, "cleanup"):
            try:
                stt_engine.cleanup()
            except Exception as e:
                print(f"[Shutdown] Error during stt_engine cleanup: {e}")
        print("👋 Exiting… (forced exit)")
        sys.exit(0)

def print_async_tasks():
    """Minimal async task list, one line per task, no table formatting."""
    tasks = []
    for t in asyncio.all_tasks():
        f = getattr(t.get_coro(), 'cr_frame', None)
        loc = f"{pathlib.Path(f.f_code.co_filename).name}:{f.f_lineno}" if f else ''
        tasks.append({
            "name": t.get_name(),
            "state": t._state,
            "coro": t.get_coro().__qualname__,
            "loc": loc
        })
    if tasks:
        print(Fore.CYAN + Style.BRIGHT + "\nAsync Tasks:")
        for t in tasks:
            name = f"{Fore.YELLOW}{t['name']}{Style.RESET_ALL}"
            state = f"{Fore.GREEN if t['state']=='PENDING' else Fore.RED}{t['state']}{Style.RESET_ALL}"
            print(f"  {name} | {state} | {t['coro']} | {t['loc']}")
    else:
        print(Fore.CYAN + Style.BRIGHT + "No async tasks running." + Style.RESET_ALL)

# =================== Main Code ===================
def main():
    import sys
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
    
    try:
        # Start the async event-based conversation loop
        asyncio.run(async_conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled))
    except KeyboardInterrupt:
        print("\n[KeyboardInterrupt] Exiting...")
        if hasattr(stt_engine, "cleanup"):
            try:
                stt_engine.cleanup()
            except Exception as e:
                print(f"[Shutdown] Error during stt_engine cleanup: {e}")
        sys.exit(0)
    logging.info("Assistant finished.")

if __name__ == "__main__":
    main()
